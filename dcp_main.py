
#2018.03.31. : stockchart 로 일단 삼성전자 과거 데이터 기록들을 blockrequest로 구현함.
#               TODO: 1. blockrequest가 아닌 request로 event처리를 해서 데이터를 받는 것을 구현할 것.
#                     2. request의 제한 갯수에 대응하여 waiting timer를 적용하는 구조 구현할 것.

#2018.04.10. : 주식 주문 체결 실시간 처리 예제 추가함. (시간이 오후 3시를 넘겨서 거래 테스트 못함.)

import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore
import win32com.client
import ctypes
import time
from enum import Enum

form_class = uic.loadUiType("dcp_main_window.ui")[0]

# common objects
g_CodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_CpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_CpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')

def dcp_init_plus_check(trade_opt) :
    
    if ctypes.windll.shell32.IsUserAnAdmin():
        print('정상: 관리자 권한으로 실행된 프로세스입니다')
    else:
        print('오류: 일반권한으로 실행됨. 관리자 권한으로 실행해 주세요.')
        return 1

    if(g_CpStatus.IsConnect == 0):
        print('PLUS가 정상적으로 연결되어 있지 않습니다.')
        return 2

    if(trade_opt == 0):
        return 0

    if(g_CpTrade.TradeInit(0) != 0):
        print('주문 초기화 실패')
        return 3

    return 0

# cp6033 : 주식 잔고 조회
class cxCp6033:
    def __init__(self, acc, accFlag):
        self.objReq = win32com.client.Dispatch('CpTrade.CpTd6033')
        self.objReq.SetInputValue(0, acc)
        self.objReq.SetInputValue(1, accFlag[0])
        self.objReq.SetInputValue(2, 50)    # 요청 건수 (최대 50)

    def request(self, result_codes):
        self.objReq.BlockRequest()

        reqStatus = self.objReq.GetDibStatus()
        reqRet = self.objReq.GetDibMsg1()
        print('6033:통신상태', '[', reqStatus, ']', '[', reqRet, ']')
        if reqStatus :
            return 0

        cnt = self.objReq.GetHeaderValue(7)

        if(cnt == 0): return

        print('종목코드 종목명 신용구분 체결잔고수량 체결장부단가 평가금액 평가손익')
        for i in range(cnt):
            code = self.objReq.GetDataValue(12, i)      #종목코드
            name = self.objReq.GetDataValue(0, i)       #종목명
            cashFlag = self.objReq.GetDataValue(1, i)   #신용구분
            date = self.objReq.GetDataValue(2, i)       #대출일
            amount = self.objReq.GetDataValue(7, i)     #체결잔고수량
            buyPrice = self.objReq.GetDataValue(17, i)  #체결장부단가
            evalValue = self.objReq.GetDataValue(9, i)  #평가금액
            evalPerc = self.objReq.GetDataValue(11, i)  #평가손익

            data = [code, name, cashFlag, date, amount, buyPrice, evalValue, evalPerc]
            result_codes.append(data)
            print(data)

    def get(self, result_code_list):
        self.request(result_code_list)

        while self.objReq.Continue:
            self.request(result_code_list)

class cxCpStockChart:
    def __init__(self):
        self.objReq = win32com.client.Dispatch('CpSysDib.StockChart')

    def set_input_values(self, stock_code, chart_type, count):
        self.objReq.SetInputValue(0, stock_code)
        self.objReq.SetInputValue(1, '2')   #개수로 조회
        self.objReq.SetInputValue(4, count)
        self.objReq.SetInputValue(5, [0, 2, 3, 4, 5, 8]) #날짜,시가,고가,저가,종가,거래량
        self.objReq.SetInputValue(6, chart_type)
        self.objReq.SetInputValue(9, '1')   #수정주가 사용


    #chart_type = ord('D')일,ort('W')주,ord('M')월, ort('m')분, ort('T')틱
    def request_by_count(self, stock_code, in_chart_type, count, result_list):
    
        if in_chart_type == 'day' : chart_type = ord('D')
        elif in_chart_type == 'week' : chart_type = ord('W')
        elif in_chart_type == 'month' : chart_type = ord('M')
        elif in_chart_type == 'minute' : chart_type = ord('m')
        elif in_chart_type == 'tick' : chart_type = ord('T')
        else : chart_type = ord('D')  #default day

        self.set_input_values( stock_code, chart_type, count)

        self.request(result_list)
        while self.objReq.Continue:
            self.request(result_list)

    def request(self, result_list):
        self.objReq.BlockRequest()

        reqStatus = self.objReq.GetDibStatus()
        reqRet = self.objReq.GetDibMsg1()
        print('6033:통신상태', '[', reqStatus, ']', '[', reqRet, ']')
        if reqStatus :
            return 0

        cnt = self.objReq.GetHeaderValue(3) #수신 갯수
        if(cnt == 0): return

        print('index', '날짜', '시가', '고가', '저가', '종가', '거래량')
        print('='*80)

        for i in range(cnt):
            day = self.objReq.GetDataValue(0, i)
            open_value = self.objReq.GetDataValue(1, i)
            high_value = self.objReq.GetDataValue(2, i)
            low_value = self.objReq.GetDataValue(3, i)
            close_value = self.objReq.GetDataValue(4, i)
            volume = self.objReq.GetDataValue(5, i)
            result_list.append([day, open_value, high_value, low_value, close_value, volume])
            print(i, day, open_value, high_value, low_value, close_value, volume)

    """
    def get(self, result_list):
        self.request(result_list)

        while self.objReq.Continue:
            self.request(result_list)
    """

# 설명: 주식 한 종목의 매수/정정/취소 주문 처리 및 실시간 시세와 주문 체결 처리 예제
#   매수주문 - 현재가/10차 호가를 구해 10차 호가로 매수 주문 냄
#   정정주문 - 누를 때 마다 호가를 9차 > 8차 > 7차 식으로 올려 정정주문 (가격은 실시간으로 업데이트 된 가격임)
#   취소주문 - 취소 주문
 
# CpEvent: 실시간 현재가 수신 클래스 - 아래 3가지 실시간 시세 수신
#       실시간 체결 현재가
#       실시간 10차 호가
#       실시간 주문 체결
# CpPBStockCur : (실시간)현재가 체결 요청 클래스
# CpPBStockBid : (실시간)현재가 10차 호가 요청 클래스
# CpPBConclusion : (실시간)주문체결 데이터 요청 클래스
# CpRPOrder : (RQ/RP)주식 매수/매도/정정 통신 클래스
# CpRPCurrentPrice : (RQ/RP)주식 현재가 통신 클래스
# OrderMain : 주문/체결에 대한 핵심 처리 클래스
#       매수/정정/취소 주문 버튼 클릭에 대한 이벤트 처리
#       실시간 주문 체결 업데이트에 따른 주문 상태 업데이트
 
# enum 주문 상태 세팅용
class orderStatus(Enum):
    nothing = 1          # 별 일 없는 상태
    newOrder = 2          # 신규 주문 낸 상태
    orderConfirm = 3      # 신규 주문 처리 확인
    modifyOrder = 4     # 정정 주문 낸 상태
    cancelOrder = 5      # 취소 주문 낸 상태
 
# 현재가와 10차 호가를 저장하기 위한 단순 저장소
class stockPricedData:
    def __init__(self):
        self.cur = 0        # 현재가
        self.offer = []     # 매도호가
        self.bid = []       # 매수호가
 
# 주문 체결 pb 기록용(종료 시 받은 데이터 print)
class orderHistoryData:
    def __init__(self):
        self.flag = ""
        self.code = ""
        self.price = 0
        self.orderamount = 0
        self.contamount = 0
        self.etc = ""
 
    def sethistory(self, flag, code, price, amount, contamount, ordernum, etc):
        self.flag = flag
        self.code = code
        self.price = price
        self.orderamount = amount
        self.contamount = contamount
        self.ordernum = ordernum
        self.etc = etc
 
    def printhistory(self):
        print(self.flag, self.code, "가격:", self.price, "수량:", self.orderamount, "체결수량:", self.contamount, "주문번호:", self.ordernum, self.etc)
 
 
 
# CpEvent: 실시간 이벤트 수신 클래스
class CpEvent:
    def set_params(self, client, name, parent):
        self.client = client   # CP 실시간 통신 object
        self.name = name       # 서비스가 다른 이벤트를 구분하기 위한 이름
        self.parent = parent   # callback 을 위해 보관
 
        # 데이터 변환용
        self.concdic = {"1" : "체결", "2" : "확인", "3" : "거부", "4" : "접수"}
        self.buyselldic = {"1" : "매도", "2" : "매수"}
        print(self.concdic)
        print(self.buyselldic)
 
    # PLUS 로 부터 실제로 시세를 수신 받는 이벤트 핸들러 
    def OnReceived(self):
        #print(self.name)
        if self.name == "stockcur" :
            # 현재가 체결 데이터 실시간 업데이트
            exFlag = self.client.GetHeaderValue(19)  # 예상체결 플래그
            cprice = self.client.GetHeaderValue(13)  # 현재가
            # 장중이 아니면 처리 안함.
            if exFlag != ord('2'):
                return
 
            # 현재가 업데이트
            self.parent.sprice.cur = cprice
            """
            print("PB > 현재가 업데이트 : ", cprice)
            """
 
            # 현재가 변경  call back 함수 호출
            self.parent.monitorPriceChange()
 
            return
 
        elif self.name == "stockbid" :
            # 현재가 10차 호가 데이터 실시간 업데이트
            dataindex = [3,4,7,8,11,12, 15,16, 19, 20, 27,28, 31,32,35,36,39,40,43,44]
            obi = 0
            for i in range(10):
                self.parent.sprice.offer[i] = self.client.GetHeaderValue(dataindex[obi])
                self.parent.sprice.bid[i] = self.client.GetHeaderValue(dataindex[obi + 1])
                obi += 2
            """
            # for debug
            for i in range(10):
                print("PB > 10차 호가 : ",i + 1, "차 매도/매수 호가: ", self.parent.sprice.offer[i], self.parent.sprice.bid[i])
            """
            return True

            # 10차 호가 변경 call back 함수 호출
            self.parent.monitorPriceChange()
 
            return
 
        elif self.name == "conclusion" :
            print(self.name)
            # 주문 체결 실시간 업데이트
            conflag = self.client.GetHeaderValue(14)    # 체결 플래그
            ordernum = self.client.GetHeaderValue(5)    # 주문번호
            amount = self.client.GetHeaderValue(3)      # 체결 수량
            price = self.client.GetHeaderValue(4)       # 가격
            code = self.client.GetHeaderValue(9)        # 종목코드
            bs = self.client.GetHeaderValue(12)         # 매수/매도 구분
            balace = self.client.GetHeaderValue(23)  # 체결 후 잔고 수량
 
            conflags = ""
            if conflag in self.concdic :
                conflags = self.concdic.get(conflag)
                print(conflags)
 
            bss = ""
            if (bs in self.buyselldic):
                bss = self.buyselldic.get(bs)
 
            print(conflags, bss, code, "주문번호:", ordernum)
            # call back 함수 호출해서 orderMain 에서 후속 처리 하게 한다.
            self.parent.monitorOrderStatus(code, ordernum, conflags, price, amount, balace)
            return
 
 
# CpPBStockCur: 실시간 현재가 요청 클래스
class CpPBStockCur:
    def __init__(self):
        self.name = "stockcur"
        self.obj = win32com.client.Dispatch("DsCbo1.StockCur")
 
    def Subscribe(self, code, sprice, parent):
        self.obj.SetInputValue(0, code)
        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, self.name, parent)
        self.obj.Subscribe()
        self.sprice = sprice
 
    def Unsubscribe(self):
        self.obj.Unsubscribe()
 
# CpPBStockBid: 실시간 10차 호가 요청 클래스
class CpPBStockBid:
    def __init__(self):
        self.name = "stockbid"
        self.obj = win32com.client.Dispatch("Dscbo1.StockJpBid")
 
    def Subscribe(self, code, sprice, parent):
        self.obj.SetInputValue(0, code)
        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, self.name, parent)
        self.obj.Subscribe()
        self.sprice = sprice
 
 
    def Unsubscribe(self):
        self.obj.Unsubscribe()
 
# CpPBConclusion: 실시간 주문 체결 수신 클래그
class CpPBConclusion:
    def __init__(self):
        self.name = "conclusion"
        self.obj = win32com.client.Dispatch("DsCbo1.CpConclusion")
 
    def Subscribe(self, parent):
        self.parent = parent
        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, self.name, parent)
        self.obj.Subscribe()
 
    def Unsubscribe(self):
        self.obj.Unsubscribe()


class CpRPOrder:
    def __init__(self):
        # 연결 여부 체크
        self.objCpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
        bConnect = self.objCpCybos.IsConnect
        if (bConnect == 0):
            print("PLUS가 정상적으로 연결되지 않음. ")
            return
 
        # 주문 초기화
        self.objTrade = win32com.client.Dispatch("CpTrade.CpTdUtil")
        initCheck = self.objTrade.TradeInit(0)
        if (initCheck != 0):
            print("주문 초기화 실패")
            return
        
        self.acc = self.objTrade.AccountNumber[0]  # 계좌번호
        self.accFlag = self.objTrade.GoodsList(self.acc, 1)  # 주식상품 구분
        print(self.acc, self.accFlag[0])
 
        # 매수/정정/취소 주문 object 생성
        self.objBuyOrder = win32com.client.Dispatch("CpTrade.CpTd0311")     # 매수
        self.objModifyOrder = win32com.client.Dispatch("CpTrade.CpTd0313")  # 정정
        self.objCancelOrder = win32com.client.Dispatch("CpTrade.CpTd0314")  # 취소
        self.orderNum = 0 # 주문 번호
 
    def buyOrder(self, code, price, amount):
        # 주식 매수 주문
        print("신규 매수", code, price, amount)
 
        self.objBuyOrder.SetInputValue(0, "2")  # 2: 매수
        self.objBuyOrder.SetInputValue(1, self.acc)  # 계좌번호
        self.objBuyOrder.SetInputValue(2, self.accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
        self.objBuyOrder.SetInputValue(3, code)  # 종목코드
        self.objBuyOrder.SetInputValue(4, amount)  # 매수수량
        self.objBuyOrder.SetInputValue(5, price)  # 주문단가 
        self.objBuyOrder.SetInputValue(7, "0")  # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
        self.objBuyOrder.SetInputValue(8, "01")  # 주문호가 구분코드 - 01: 보통
 
        # 매수 주문 요청
        self.objBuyOrder.BlockRequest()
 
        rqStatus = self.objBuyOrder.GetDibStatus()
        rqRet = self.objBuyOrder.GetDibMsg1()
        print("통신상태", rqStatus, rqRet)
        if rqStatus != 0:
            return False
 
        # 주의: 매수 주문에  대한 구체적인 처리는 cpconclusion 으로 파악해야 한다.
        return True
 
    def modifyOrder(self, ordernum, code, price):
        # 주식 정정 주문
        print("정정주문", ordernum, code, price)
        self.objModifyOrder.SetInputValue(1, ordernum)  #  원주문 번호 - 정정을 하려는 주문 번호
        self.objModifyOrder.SetInputValue(2, self.acc)  # 상품구분 - 주식 상품 중 첫번째
        self.objModifyOrder.SetInputValue(3, self.accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
        self.objModifyOrder.SetInputValue(4, code)  # 종목코드
        self.objModifyOrder.SetInputValue(5, 0)  # 정정 수량, 0 이면 잔량 정정임
        self.objModifyOrder.SetInputValue(6, price)  #  정정주문단가
 
        # 정정주문 요청
        self.objModifyOrder.BlockRequest()
 
        rqStatus = self.objModifyOrder.GetDibStatus()
        rqRet = self.objModifyOrder.GetDibMsg1()
        print("통신상태", rqStatus, rqRet)
        if rqStatus != 0:
            return False
 
        # 새로운 주문 번호 구한다.
        self.orderNum = self.objModifyOrder.GetHeaderValue(7)
 
    def cancelOrder(self, ordernum, code):
        # 주식 취소 주문
        print("취소주문", ordernum, code)
        self.objCancelOrder.SetInputValue(1, ordernum)  #  원주문 번호 - 정정을 하려는 주문 번호
        self.objCancelOrder.SetInputValue(2, self.acc)  # 상품구분 - 주식 상품 중 첫번째
        self.objCancelOrder.SetInputValue(3, self.accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
        self.objCancelOrder.SetInputValue(4, code)  # 종목코드
        self.objCancelOrder.SetInputValue(5, 0)  # 정정 수량, 0 이면 잔량 취소임
 
        # 취소주문 요청
        self.objCancelOrder.BlockRequest()
 
        rqStatus = self.objCancelOrder.GetDibStatus()
        rqRet = self.objCancelOrder.GetDibMsg1()
        print("통신상태", rqStatus, rqRet)
        if rqStatus != 0:
            return False
 

class CpRPCurrentPrice:
    def __init__(self):
        self.objCpCybos = win32com.client.Dispatch('CpUtil.CpCybos')
        bConnect = self.objCpCybos.IsConnect
        if(bConnect == 0):
            print("plus가 정상적으로 연결되지 않음")
            return
        self.objStockMst = win32com.client.Dispatch('DsCbo1.StockMst')
        self.objStockjpbid = win32com.client.Dispatch('DsCbo1.StockJpBid2')
        return

    def Request(self, code, rtMst):
        #현재가 통신
        self.objStockMst.SetInputValue(0, code)
        self.objStockMst.BlockRequest()

        #10차호가 통신
        self.objStockjpbid.SetInputValue(0, code)
        self.objStockjpbid.BlockRequest()

        print('통신상태', self.objStockMst.GetDibStatus(), self.objStockMst.GetDibMsg1())
        if self.objStockMst.GetDibStatus() != 0:
            return False
        print('통신상태', self.objStockjpbid.GetDibStatus(), self.objStockjpbid.GetDibMsg1())
        if self.objStockjpbid.GetDibStatus() != 0:
            return False

        #수신받은 현재가 정보를 rtMst에 저장
        rtMst.cur = self.objStockMst.GetHeaderValue(11) #종가
        #10차호가
        for i in range(10):
            rtMst.offer.append(self.objStockjpbid.GetDataValue(0, i))   #매도호가
            rtMst.bid.append(self.objStockjpbid.GetDataValue(1, i))     #매수호가

        #debug
        for i in range(10):
            print(i+1, '차 매도/매수 호가:', rtMst.offer[i], rtMst.bid[i])

        return True

class cxOrderMain():
    def __init__(self):
        self.isSB = 0       #실시간 처리
        self.initOrder()    #주문상태 초기화

        self.sprice = stockPricedData() #주문 현재가/10차 호가 저장 (실시간 업데이트)
        self.cporder = CpRPOrder()      #주문 통신 object
        
        #실시간 통신 object
        self.cur = CpPBStockCur()
        self.bid = CpPBStockBid()

        #주문체결은 미리 실시간 요청
        self.conclusion = CpPBConclusion()
        self.conclusion.Subscribe(self)

        self.history = []

    def stopSubscribe(self):
        if self.isSB != 0 :
            self.cur.Unsubscribe()
            self.bid.Unsubscribe()
        self.isSB = 0

    def BuyOrder(self):
        self.stopSubscribe()
        self.code = 'A003540'   #테스트용 종목 코드 : 대신증권
        self.buyamount = 1      #주문 수량
        
        #1 현재가 구하기
        price = CpRPCurrentPrice()
        if price.Request(self.code, self.sprice) == False :
            print("현재가 통신 실패")
            self.initOrder()
            return

        print("신규 매수 주문 - ", self.orderNonce + 1, "차 매수 호가", + self.sprice.bid[self.orderNonce])
        bResult = self.cporder.buyOrder(self.code, self.sprice.bid[self.orderNonce], self.buyamount)

        if bResult == False :
            print('주문실패')
            self.initOrder()
            return

        self.orderStatus = orderStatus.newOrder #주문상태 업데이트

        #실시간 통신 요청
        self.cur.Subscribe(self.code, self.sprice, self)
        self.bid.Subscribe(self.code, self.sprice, self)
        self.isSB = 1

    #정정주문
    def ModifyOrder(self):
        if not(self.orderStatus == orderStatus.orderConfirm):
            print("정정주문 확인 불가 상태")
            return

        if self.ordernum == 0 :
            print('주문번호가 없습니다')
            return

        #정정주문 할 때 마다 1호가 씩 올린다.
        self.orderNonce -= 1
        if self.orderNonce <= 0 :
            self.orderNonce = 0
        
        print('정정주문 - ', self.orderNonce + 1, '차 매수호가', +self.sprice.bid[self.orderNonce])
        bResult = self.cporder.modifyOrder(self.ordernum, self.code, self.sprice.bid[self.orderNonce])
        if bResult == False :
            print('정정주문 실패')
            return

        #주문 상태 업데이트
        self.orderStatus = orderStatus.modifyOrder

        #정정주문은 거래소에서 거부당할 수 있어 확인/거부 여부를 반드시 확인해야 함.

        return

    def CancelOrder(self):
        if not(self.orderStatus == orderStatus.orderConfirm):
            print('취소주문 확인 불가 상태')
            return

        if self.ordernum == 0 :
            print('주문번호가 없습니다')
            return

        #취소주문
        bResult = self.cporder.cancelOrder(self.ordernum, self.code)
        if bResult == False:
            print("취소주문 실패")
            return

        self.orderStatus = orderStatus.cancelOrder #주문상태 업데이트

        #취소주문은 거래소에서 거부당할 수 있어 확인/거부 여부를 반드시 확인해야 함.
        return

    def clearAll(self):
        self.initOrder()
        self.stopSubscribe()
        self.conclusion.Unsubscribe()

        #debug
        if(len(self.history)) :
            print('주문 내역 정리 =========================')
            for i in range(0, len(self.history)):
                self.history[i].printhistory()

        self.history = []

        return

    def initOrder(self):
        #주문 정보 초기화
        self.orderStatus = orderStatus.nothing
        self.ordernum = 0       #주문 번호
        self.remainAmount = 0   #주문 후 미체결 수량
        self.orderNonce = 9     #매수 주문 호가 조정 변수 (9>8>7..순으로 호가 조정)

    def monitorPriceChange(self):
        #이곳에서 시세 변경에 대한 감시 등의 로직 추가 고려
        return

    def monitorOrderStatus(self, code, ordernum, conflags, price, amount, balance):
        print('주문:', code, ordernum, conflags, price, amount, balance)
        if self.orderStatus == orderStatus.nothing:
            return
        #체결: 체결시 체결 수량/미체결 수량 게산
        if conflags == '체결' :
            self.remainAmount -= amount
            if self.orderStatus == orderStatus.orderConfirm:
                print('주문체결됨', '수량', amount, '잔고량:', balance, '미체결수량', self.remainAmount)

            if self.remainAmount <= 0 : #전량 체결됨
                self.initOrder()

            #debug
            history = orderHistoryData()
            history.sethistory(conflags, code, price, self.remainAmount, amount, ordernum, "")
            self.history.append(history)

        #접수 : 신규주문 > 접수 : ->주문번호, 주문 정상 처리
        elif conflags == '접수' :
            if self.orderStatus == orderStatus.newOrder :
                self.ordernum = ordernum #주문번호 업데이트
                self.remainAmount = amount #주문 후  미체결 수량
                self.orderStatus = orderStatus.orderConfirm

                #debug
                history = orderHistoryData()
                history.sethistory(conflags, code, price, amount, 0, ordernum, '신규 매수')
                self.history.append(history)
                history.printhistory()

        #확인: 정정/취소 주문 > 확인 : -> 정정/취소 주문 정상 처리 확인
        elif conflags == '확인':
            etc = ''
            if self.orderStatus == orderStatus.modifyOrder:     #정정확인
                self.ordernum = ordernum #주문번호 업데이트
                self.orderStatus = orderStatus.orderConfirm
                etc = '정정확인'
            elif self.orderStatus == orderStatus.cancelOrder :  #취소확인
                self.initOrder()
                etc = '취소확인'

            #debug
            history = orderHistoryData()
            print(code, price)
            print(self.remainAmount, ordernum)
            history.sethistory(conflags, code, price, self.remainAmount, 0, ordernum, etc)
            self.history.append(history)
            history.printhistory()

        elif conflags == '거부':
            if self.orderStatus == orderStatus.modifyOrder or self.orderStatus == orderStatus.cancelOrder :
                print("주문거부 발생, 반드시 확인 필요")
                self.orderStatus = orderStatus.newOrder #주문 상태를 이전으로 돌림

        #debug
        history = orderHistoryData()
        history.sethistory(conflags, code, price, amount, 0, ordernum, '')
        self.history.append(history)
        history.printhistory()

        return

class cxDcpMainWindow(QDialog, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        if dcp_init_plus_check(1) :
            exit()

        self.account = g_CpTrade.AccountNumber[0]
        self.accFlag = g_CpTrade.GoodsList(self.account, 1)
        #print('계좌번호:', self.account, '상품구분번호:', self.accFlag)

        self.label.setText('계좌번호: %s 상품구분번호: %s'%(self.account, self.accFlag))

        self.orderMain = cxOrderMain()

        self.btnZango.clicked.connect(self.btnZango_clicked)
        self.btnGetStockAll.clicked.connect(self.btnGetStockAll_clicked)
        self.btnExit.clicked.connect(self.btnExit_clicked)
        self.btnBuy.clicked.connect(self.btnBuy_clicked)
        self.btnModify.clicked.connect(self.btnModify_clicked)
        self.btnCancel.clicked.connect(self.btnCancel_clicked)

        self.timer = QtCore.QTimer(self)
        self.timer.start(500)               #500 milisecond
        self.timer.timeout.connect(self.queueTime)

    def queueTime(self):
        #print('timeout')
        #print('timeout', time.strftime("%H:%M:%S"))
        pass

    def btnZango_clicked(self):
        data_list = []
        cp6033 = cxCp6033(self.account, self.accFlag)
        cp6033.get(data_list)
        del cp6033
        del data_list

    def btnBuy_clicked(self):
        print("Buy Clicked.")
        self.orderMain.BuyOrder()

    def btnModify_clicked(self):
        print("Modify clicked.")
        self.orderMain.ModifyOrder()

    def btnCancel_clicked(self):
        print("Cancel clicked.")
        self.orderMain.CancelOrder()

    def btnGetStockAll_clicked(self):
        """
        KOSPI_codeList = g_CodeMgr.GetStockListByMarket(1)
        KOSDAQ_codeList = g_CodeMgr.GetStockListByMarket(2)

        count_num = 0
        print('순서, 종목코드, 구분코드, 상태, 종목명, 자본금규모, 그룹(계열사)코드, 가격')
        for i, code in enumerate(KOSPI_codeList):
            code2 = g_CodeMgr.GetStockSectionKind(code)
            if not ((code2 == 1) or (code2 == 14) or (code2 == 15)) : continue 
            name = g_CodeMgr.CodeToName(code)
            status = g_CodeMgr.GetStockControlKind(code)
            if status != 0 : continue
            sprvs = g_CodeMgr.GetStockSupervisionKind(code)
            if sprvs != 0 : continue
            statusKind = g_CodeMgr.GetStockStatusKind(code)
            if statusKind != 0 : continue
            capital = g_CodeMgr.GetStockCapital(code)
            stdPrice = g_CodeMgr.GetStockStdPrice(code)
            groupCode = g_CodeMgr.GetStockGroupCode(code)
            if ((code2 == 14) or (code2 == 15)) :
                print('최소변동 호가단위 (TickUnit)', g_CodeMgr.GetTickUnit(code))
                print('1계약당 최소가격 변동폭', g_CodeMgr.GetTickValue(code))
            print(i, code, code2, name, capital, groupCode, stdPrice)
            count_num += 1
            if count_num%30 == 0 :
                ans = input().split(' ')[0]

        print('총 개수: ', count_num)

        print('장 시작 시간', g_CodeMgr.GetMarketStartTime())
        print('장 마감 시간', g_CodeMgr.GetMarketEndTime())
        """
        cpStockChart = cxCpStockChart()

        chart_data_list = []
        cpStockChart.request_by_count('A005930', 'day', 100000, chart_data_list)    #삼성전자


    def btnExit_clicked(self):
        exit()
        return

if __name__ == '__main__' :
    app = QApplication(sys.argv)
    dcp_main_window = cxDcpMainWindow()
    dcp_main_window.show()
    sys.exit(app.exec_())
