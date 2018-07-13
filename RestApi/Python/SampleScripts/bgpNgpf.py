
# PLEASE READ DISCLAIMER
#
#    This is a sample script for demo and reference purpose only.
#    It is subject to change for content updates without warning.
#
# REQUIREMENTS
#    - Python modules: requests
#    - Python 2.7 minimum
#
# DESCRIPTION
#    This sample script demonstrates:
#        - REST API configurations using two back-to-back Ixia ports.
#        - Connecting to Windows IxNetwork API server or Linux API server.
#
#        - Verify for sufficient amount of port licenses before testing.
#        - Verify port ownership.
#        - Configure two IPv4/BGP Topology Groups
#        - Start protocols
#        - Verify BGP protocol sessions
#        - Create a Traffic Item
#        - Apply Traffic
#        - Start Traffic
#        - Get stats
#
# USAGE
#    python <script>.py windows
#    python <script>.py linux

import sys, os, traceback

# These  modules are one level above.
sys.path.insert(0, (os.path.dirname(os.path.abspath(__file__).replace('SampleScripts', 'Modules'))))
from IxNetRestApi import *
from IxNetRestApiPortMgmt import PortMgmt
from IxNetRestApiTraffic import Traffic
from IxNetRestApiProtocol import Protocol
from IxNetRestApiStatistics import Statistics

# Default the API server to either windows or linux.
osPlatform = 'windows'

if len(sys.argv) > 1:
    if sys.argv[1] not in ['windows', 'windowsConnectionMgr', 'linux']:
        sys.exit("\nError: %s is not a known option. Choices are 'windows' or 'linux'." % sys.argv[1])
    osPlatform = sys.argv[1]

try:
    #---------- Preference Settings --------------

    forceTakePortOwnership = True
    releasePortsWhenDone = False
    enableDebugTracing = True
    deleteSessionAfterTest = True ;# For Windows Connection Mgr and Linux API server only

    # Set configLicense to False if:
    #    - You are using a Linux based XGS chassis and the licenses are activated in the chassis.
    #    - Or the license settings are configured in the Windows IxNetwork GUI in Preferences.
    # Set configLicense to True if:
    #    - You are using IxVM chassis/ports and OVA Linux API server and the licenses are not activated in the vm chassis.
    configLicense = True
    licenseServerIp = '192.168.70.3'
    licenseModel = 'subscription'
    licenseTier = 'tier3'

    ixChassisIp = '192.168.70.11'
    # [chassisIp, cardNumber, slotNumber]
    portList = [[ixChassisIp, '1', '1'], [ixChassisIp, '2', '1']]

    if osPlatform == 'linux':
        mainObj = Connect(apiServerIp='192.168.70.108',
                          serverIpPort='443',
                          username='admin',
                          password='admin',
                          deleteSessionAfterTest=deleteSessionAfterTest,
                          verifySslCert=False,
                          serverOs=osPlatform
                          )

    if osPlatform in ['windows', 'windowsConnectionMgr']:
        mainObj = Connect(apiServerIp='192.168.70.3',
                          serverIpPort='11009',
                          serverOs=osPlatform,
                          deleteSessionAfterTest=True
                          )

    #---------- Preference Settings End --------------

    portObj = PortMgmt(mainObj)
    portObj.connectIxChassis(ixChassisIp)

    if portObj.arePortsAvailable(portList, raiseException=False) != 0:
        if forceTakePortOwnership == True:
            portObj.releasePorts(portList)
            portObj.clearPortOwnership(portList)
        else:
            raise IxNetRestApiException('Ports are owned by another user and forceTakePortOwnership is set to False')

    mainObj.newBlankConfig()

    if configLicense == True:
        portObj.releaseAllPorts()
        mainObj.configLicenseServerDetails([licenseServerIp], licenseModel, licenseTier)

    portObj.assignPorts(portList)

    protocolObj = Protocol(mainObj)
    topologyObj1 = protocolObj.createTopologyNgpf(portList=[portList[0]], topologyName='Topo1')

    deviceGroupObj1 = protocolObj.createDeviceGroupNgpf(topologyObj1,
                                                        multiplier=1,
                                                        deviceGroupName='DG1')
                                                  
    topologyObj2 = protocolObj.createTopologyNgpf(portList=[portList[1]], topologyName='Topo2')

    deviceGroupObj2 = protocolObj.createDeviceGroupNgpf(topologyObj2,
                                                        multiplier=1,
                                                        deviceGroupName='DG2')

    ethernetObj1 = protocolObj.configEthernetNgpf(deviceGroupObj1,
                                                  ethernetName='MyEth1',
                                                  macAddress={'start': '00:01:01:00:00:01',
                                                              'direction': 'increment',
                                                              'step': '00:00:00:00:00:01'},
                                                  macAddressPortStep='disabled',
                                                  vlanId={'start': 103,
                                                          'direction': 'increment',
                                                          'step':0})

    ethernetObj2 = protocolObj.configEthernetNgpf(deviceGroupObj2,
                                                  ethernetName='MyEth2',
                                                  macAddress={'start': '00:01:02:00:00:01',
                                                              'direction': 'increment',
                                                              'step': '00:00:00:00:00:01'},
                                                  macAddressPortStep='disabled',
                                                  vlanId={'start': 103,
                                                          'direction': 'increment',
                                                          'step':0})

    ipv4Obj1 = protocolObj.configIpv4Ngpf(ethernetObj1,
                                          ipv4Address={'start': '1.1.1.1',
                                                       'direction': 'increment',
                                                       'step': '0.0.0.1'},
                                          ipv4AddressPortStep='disabled',
                                          gateway={'start': '1.1.1.2',
                                                   'direction': 'increment',
                                                   'step': '0.0.0.0'},
                                          gatewayPortStep='disabled',
                                          prefix=24,
                                          resolveGateway=True)

    ipv4Obj2 = protocolObj.configIpv4Ngpf(ethernetObj2,
                                          ipv4Address={'start': '1.1.1.2',
                                                       'direction': 'increment',
                                                       'step': '0.0.0.1'},
                                          ipv4AddressPortStep='disabled',
                                          gateway={'start': '1.1.1.1',
                                                   'direction': 'increment',
                                                   'step': '0.0.0.0'},
                                          gatewayPortStep='disabled',
                                          prefix=24,
                                          resolveGateway=True)

    bgpObj1 = protocolObj.configBgp(ipv4Obj1,
                                    name = 'bgp_1',
                                    enableBgp = True,
                                    holdTimer = 90,
                                    dutIp={'start': '1.1.1.2', 'direction': 'increment', 'step': '0.0.0.0'},
                                    localAs2Bytes = 101,
                                    #localAs4Bytes = 108,
                                    #enable4ByteAs = True,
                                    enableGracefulRestart = False,
                                    restartTime = 45,
                                    type = 'internal',
                                    enableBgpIdSameasRouterId = True)

    bgpObj2 = protocolObj.configBgp(ipv4Obj2,
                                    name = 'bgp_2',
                                    enableBgp = True,
                                    holdTimer = 90,
                                    dutIp={'start': '1.1.1.1', 'direction': 'increment', 'step': '0.0.0.0'},
                                    localAs2Bytes = 101,
                                    enableGracefulRestart = False,
                                    restartTime = 45,
                                    type = 'internal',
                                    enableBgpIdSameasRouterId = True)

    networkGroupObj1 = protocolObj.configNetworkGroup(create=deviceGroupObj1,
                                                      name='networkGroup1',
                                                      multiplier = 100,
                                                      networkAddress = {'start': '160.1.0.0',
                                                                        'step': '0.0.0.1',
                                                                        'direction': 'increment'},
                                                      prefixLength = 32)

    networkGroupObj2 = protocolObj.configNetworkGroup(create=deviceGroupObj2,
                                                  name='networkGroup2',
                                                  multiplier = 100,
                                                  networkAddress = {'start': '180.1.0.0',
                                                                    'step': '0.0.0.1',
                                                                    'direction': 'increment'},
                                                  prefixLength = 32)

    protocolObj.startAllProtocols()
    protocolObj.verifyAllProtocolSessionsNgpf()

    # For all parameter options, go to the API configTrafficItem.
    # mode = create or modify
    # Note: Check API configTrafficItem for options.
    trafficObj = Traffic(mainObj)
    trafficStatus = trafficObj.configTrafficItem(
        mode='create',
        trafficItem = {
            'name': 'Topo1 to Topo2',
            'trafficType': 'ipv4',
            'biDirectional': True,
            'srcDestMesh': 'one-to-one',
            'routeMesh': 'oneToOne',
            'allowSelfDestined': False,
            'trackBy': ['flowGroup0', 'vlanVlanId0']},
        endpoints = [{'name': 'Flow-Group-1',
                      'sources': [topologyObj1],
                      'destinations': [topologyObj2]
                  }],
        # transmissionType:   fixedFrameCount|continuous
        # frameRateType:      percentLineRate|framesPerSecond
        # portDistribution:   applyRateToAll|splitRateEvenly
        # streamDistribution: splitRateEvenly|applyRateToAll
        configElements = [{'transmissionType': 'fixedFrameCount',
                           'frameCount': 50000,
                           'frameRate': 88,
                           'duration': 10,
                           'frameRateType': 'percentLineRate',
                           'frameSize': 128,
                           'portDistribution': 'applyRateToAll',
                           'streamDistribution': 'splitRateEvenly'
                       }])

    trafficItemObj   = trafficStatus[0]
    endpointObj      = trafficStatus[1][0]
    configElementObj = trafficStatus[2][0]

    trafficObj.startTraffic(regenerateTraffic=True, applyTraffic=True)

    # Check the traffic state before getting stats.
    #    Use one of the below APIs based on what you expect the traffic state should be before calling stats.
    #    'stopped': If you expect traffic to be stopped such as for fixedFrameCount and fixedDuration.
    #    'started': If you expect traffic to be started such as in continuous mode.
    trafficObj.checkTrafficState(expectedState=['stopped'], timeout=45)
    #trafficObj.checkTrafficState(expectedState=['started'], timeout=45)

    statObj = Statistics(mainObj)
    stats = statObj.getStats(viewName='Flow Statistics')

    print('\n{txPort:10} {txFrames:15} {rxPort:10} {rxFrames:15} {frameLoss:10}'.format(
        txPort='txPort', txFrames='txFrames', rxPort='rxPort', rxFrames='rxFrames', frameLoss='frameLoss'))
    print('-'*90)

    for flowGroup,values in stats.items():
        txPort = values['Tx Port']
        rxPort = values['Rx Port']
        txFrames = values['Tx Frames']
        rxFrames = values['Rx Frames']
        frameLoss = values['Frames Delta']

        print('{txPort:10} {txFrames:15} {rxPort:10} {rxFrames:15} {frameLoss:10} '.format(
            txPort=txPort, txFrames=txFrames, rxPort=rxPort, rxFrames=rxFrames, frameLoss=frameLoss))

    if releasePortsWhenDone == True:
        portObj.releasePorts(portList)

    if osPlatform == 'linux':
        mainObj.linuxServerStopAndDeleteSession()

    if osPlatform == 'windowsConnectionMgr':
        mainObj.deleteSession()

except (IxNetRestApiException, Exception, KeyboardInterrupt) as errMsg:
    if enableDebugTracing:
        if not bool(re.search('ConnectionError', traceback.format_exc())):
            print('\n%s' % traceback.format_exc())

    if 'mainObj' in locals() and osPlatform == 'linux':
        if deleteSessionAfterTest:
            mainObj.linuxServerStopAndDeleteSession()

    if 'mainObj' in locals() and osPlatform in ['windows', 'windowsConnectionMgr']:
        if releasePortsWhenDone and forceTakePortOwnership:
            portObj.releasePorts(portList)

        if osPlatform == 'windowsConnectionMgr':
            if deleteSessionAfterTest:
                mainObj.deleteSession()
