
#2018.03.31. : stockchart 로 일단 삼성전자 과거 데이터 기록들을 blockrequest로 구현함.
#               TODO: 1. blockrequest가 아닌 request로 event처리를 해서 데이터를 받는 것을 구현할 것.
#                     2. request의 제한 갯수에 대응하여 waiting timer를 적용하는 구조 구현할 것.

import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore
import win32com.client
import ctypes
import time

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

class cxDcpMainWindow(QDialog, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        if dcp_init_plus_check(1) :
            exit()

        self.account = g_CpTrade.AccountNumber[0]
        self.accFlag = g_CpTrade.GoodsList(self.account, 1)
        #print('계좌번호:', self.account, '상품구분번호:', self.accFlag)
        
        #self.init_UI()

        self.label.setText('계좌번호: %s 상품구분번호: %s'%(self.account, self.accFlag))
        self.btnZango.clicked.connect(self.btnZango_clicked)
        self.btnGetStockAll.clicked.connect(self.btnGetStockAll_clicked)
        self.btnExit.clicked.connect(self.btnExit_clicked)

        self.timer = QtCore.QTimer(self)
        self.timer.start(500)               #500 milisecond
        self.timer.timeout.connect(self.queueTime)

    def queueTime(self):
        #print('timeout')
        print('timeout', time.strftime("%H:%M:%S"))

    def btnZango_clicked(self):
        data_list = []
        cp6033 = cxCp6033(self.account, self.accFlag)
        cp6033.get(data_list)
        del cp6033
        del data_list

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
