#!/usr/bin/env python
import sys
sys.path.insert(1, "../")
from myutils import BetterConfigParser, sClient, decode, printer, preexec, testchain,scp
from myutils import Testboard as Testboarddefinition
from time import strftime, localtime
import time
from shutil import copytree,rmtree, copyfile
import paramiko
import os
import subprocess
import argparse
import environment
import xray_agente
import psi_agente
import shutil
import coolingBox_agente
import analysis_agente
import highVoltage_agente
import watchDog_agente
import signal
import tarfile
#import scp

los_agentes = []

def killChildren():
    print "Killing clients ..."

    # Ask the client processes to exit
    for agente in los_agentes:
        agente.request_client_exit()

    try:
        for subscription in subscriptionList:
            client.send(subscription,':prog:exit\n')
        time.sleep(1)
    except:
        pass

    # Close the subsystem client connection
    try:
        client.closeConnection()
    except:
        pass

    # Kill the client processes
    for agente in los_agentes:
        try:
            agente.kill_client()
        except:
            agente.log.warning("Could not kill %s" % agente.client_name)

def handler(signum, frame):
    print 'Signal handler called with signal %s' % signum
    killChildren();
    sys.exit(0)

#signal.signal(signal.SIGINT, handler)

try:
    #get timestamp
    timestamp = int(time.time())
    #------------some configuration--------------

    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", dest="configDir",
                           help="specify directory containing config files e.g. ../config/",
                           default="../config/")

    args = parser.parse_args()
    configDir= args.configDir
    try:
        os.access(configDir,os.R_OK)
    except:
        raise Exception('configDir \'%s\' is not accessible'%configDir)
        #sys.exit()
        #raise SystemExit

    #load config
    configFile = configDir+'/elComandante.conf'
    config = BetterConfigParser()
    config.read(configFile)
    #load init
    iniFile = configDir+'/elComandante.ini'
    init = BetterConfigParser()
    init.read(iniFile)

    Directories={}

    Directories['configDir'] = configDir
    Directories['baseDir'] = config.get('Directories','baseDir')
    Directories['testdefDir'] = config.get('Directories','testDefinitions')
    Directories['dataDir'] = config.get('Directories','dataDir')
    Directories['defaultParameters'] = config.get('Directories','defaultParameters')
    Directories['subserverDir'] = config.get('Directories','subserverDir')
    Directories['keithleyDir'] = config.get('Directories','keithleyDir')
    Directories['jumoDir'] = config.get('Directories','jumoDir')
    Directories['logDir'] = Directories['dataDir']+'/logfiles/'
    config.Directories = Directories

    for dir in Directories:
        #if "$configDir$" in Directories[dir]:
        Directories[dir] = os.path.abspath(Directories[dir].replace("$configDir$",configDir))
    try:
        os.stat(Directories['dataDir'])
    except:
        os.mkdir(Directories['dataDir'])
    try:
        os.stat(Directories['subserverDir'])
    except:
        os.mkdir(Directories['subserverDir'])

    try:
        logFiles = (os.listdir(Directories['logDir']))
        nLogFiles = len(logFiles)
        print nLogFiles
    except:
        os.mkdir(Directories['logDir'])
    else:
        print nLogFiles
        if nLogFiles>0:
            answer = raw_input('Do you want to overwrite \'%s\'? [y]es or [n]o\n\t'%logFiles)
            if 'y' in answer.lower():
                rmtree(Directories['logDir'])
                os.mkdir(Directories['logDir'])
            else:
                raise Exception('LogDir is not empty. Please clean logDir: %s'%Directories['logDir'])

    #initialise Logger
    Logger = printer()
    Logger.set_name("elComandanteLog")
    Logger.timestamp = timestamp
    Logger.set_logfile('%s/elComandante.log'%(Directories['logDir']))
    Logger.printw()
    Logger<<'Set LogFile to %s'%Logger.f

    #check if subsystem server is running, if not START subserver

    if os.system("ps -ef | grep -v grep | grep subserver > /dev/null"):
        os.system("cd %s && subserver"%(Directories['subserverDir']))
        if os.system("ps -ef | grep -v grep | grep subserver"):
            raise Exception("Could not start subserver");

    #check if subsystem server is running, if not START subserver
    #if not "subserver.pid" in os.listdir("/var/tmp"):
    #    Logger << "Starting subserver ..."
    #    os.system("cd %s && subserver"%(Directories['subserverDir']))
    #    time.sleep(0.2)
    #    #check again whether it is running
    #    if not "subserver.pid" in os.listdir("/var/tmp"):
    #        raise Exception("Could not start subserver")
    Logger << "Subserver is running."
    Logger.printn()

    #read subserver settings
    serverZiel=config.get('subsystem','Ziel')
    Port = int(config.get('subsystem','Port'))
    serverPort = int(config.get('subsystem','serverPort'))
    coolingBoxSubscription = config.get('subsystem','coolingBoxSubscription')
    keithleySubscription = config.get('subsystem','keithleySubscription')
    psiSubscription = config.get('subsystem','psiSubscription')
    xraySubscription = config.get('subsystem','xraySubscription')
    analysisSubscription = config.get('subsystem','analysisSubscription')

    #create subserver client
    client = sClient(serverZiel,serverPort,"elComandante")

    # Create agentes that are responsible for client processes
    los_agentes.append(psi_agente.psi_agente(timestamp, Logger, client))
    los_agentes.append(highVoltage_agente.highVoltage_agente(timestamp,Logger,client))
    los_agentes.append(watchDog_agente.watchDog_agente(timestamp,Logger,client))
    if init.getboolean("Xray", "XrayUse"):
        los_agentes.append(xray_agente.xray_agente(timestamp, Logger, client))
    los_agentes.append(analysis_agente.analysis_agente(timestamp, Logger, client))
    if init.getboolean("CoolingBox", "CoolingBoxUse"):
        los_agentes.append(coolingBox_agente.coolingBox_agente(timestamp, Logger,client))

    # Make the agentes read their configuration and initialization parameters
    for agente in los_agentes:
        Logger << "Setting up agente %s ..." % agente.agente_name
        agente.setup_dir(Directories)
        agente.setup_configuration(config)
        agente.setup_initialization(init)
    Logger.printn()

    #subscribe subscriptions
    subscriptionList = []
    if init.getboolean("CoolingBox", "CoolingBoxUse"):
        subscriptionList.append(coolingBoxSubscription)
    for subscription in subscriptionList:
        client.subscribe(subscription)

    for agente in los_agentes:
        agente.subscribe()

    #directory config
    #get list of tests to do:
    testlist=init.get('Tests','Test')
    test_chain = testchain.parse_test_list(testlist)
    testlist= testlist.split(',')
    while '' in testlist:
            testlist.remove('')

    # Get default parameter directories
    dir_list = []
    tb = 0
    while True:
        try:
            module_type = init.get("ModuleType", "TB" + `tb`)
            dir = config.get("defaultParameters", module_type)
        except:
            break
        else:
            dir = Directories['defaultParameters'] + '/' + dir
            dir_list.append(dir)
            tb += 1
    test_chain.parameter_dir = dir_list

    #-------------------------------------

    def setupParentDir(timestamp,Testboard,init):
        Testboard.dataDir = Directories['dataDir']
        if init.has_option('Tests','TestDescription'):
            Testboard.moduleDir = '%s_%s_%s_%s'%(Testboard.module,init.get('Tests','TestDescription'),strftime("%Y-%m-%d_%Hh%Mm",localtime(timestamp)),timestamp)
        else:
            Testboard.moduleDir = '%s_%s_%s'%(Testboard.module,strftime("%Y-%m-%d_%Hh%Mm",localtime(timestamp)),timestamp)
        try:
            os.stat(Testboard.parentDir)
        except:
            os.mkdir(Testboard.parentDir)
        return Testboard.parentDir

    def wait_until_finished(los_agentes):
        finished = False
        while not finished:
            time.sleep(1.0)
            finished = all([agente.check_finished() for agente in los_agentes])
            output = ' \t'
            for agente in los_agentes:
                output += '%s: %s\t'%(agente.agente_name,int(agente.check_finished()))
            if not finished:
                sys.stdout.write('%s\r' %output)
            sys.stdout.flush()

    # Check whether the client is already running before trying to start it
    Logger << "Checking whether clients are runnning ..."
    for agente in los_agentes:
        agente.check_client_running()

    for agente in los_agentes:
        agente.start_client(timestamp)
    Logger.printn()#        self.parentDir='.'

    # Check the client subscriptions
    Logger << "Checking subscriptions of the clients ..."
    time.sleep(2)
    for subscription in subscriptionList:
        if not client.checkSubscription(subscription):
            raise Exception("Cannot read from %s subscription"%subscription)
        else:
            Logger << "\t%s is answering." % subscription
    for agente in los_agentes:
        if not agente.check_subscription():
            raise Exception("Cannot read from %s subscription" % agente.subscription)
        else:
            Logger << "\t%s is answering." % agente.subscription

    #-------------SETUP TESTBOARDS----------------
    Logger.printv()
    Logger << 'The following testboards with modules were found:'
    Logger.printn()
    #ToDo:
    for Testboard in los_agentes[0].Testboards:
            parentDir=setupParentDir(timestamp,Testboard,init)
            Logger << '\t- Testboard %s at address %s with module %s'%(Testboard.slot,Testboard.address,Testboard.module)

    Logger.printn()

    test = test_chain.next()
    while test:
        if test.test_str.find('@')>=0:
            whichtest, env = test.test_str.split('@')
        else:
            whichtest = test.test_str
            env = 17.0
        if whichtest== "IV":
            test_str_list = []
            for Testboard in los_agentes[0].Testboards:
                test_str_list.append('%s_TB%s@%s' % (whichtest, Testboard.slot, env))
            test.multiply(test_str_list)
        test = test.next()

    Logger << 'The following tests will be executed:'
    Logger.printn()
    test = test_chain.next()
    while test:
        Logger << "\t- %s" % test.test_str
        test = test.next()

    Logger.printv()

    #--------------LOOP over TESTS-----------------

    test = test_chain.next()
    while test:
        env = environment.environment(test.test_str, init)
        test.environment = env
        test.testname = test.test_str.split("@")[0]

        for agente in los_agentes:
            agente.set_test(test)

        # Prepare for the tests
        Logger << "Preparing test %s ..." % test.test_str
        for agente in los_agentes:
            agente.prepare_test(test.test_str, env)
        wait_until_finished(los_agentes)

        Logger.printn()

        # Execute tests
        Logger << "Executing test %s ..." % test.test_str
        for agente in los_agentes:
            agente.execute_test()
            time.sleep(1.0)
        wait_until_finished(los_agentes)

        Logger.printn()

        # Cleanup tests
        Logger << "Cleaning up after test %s ..." % test.test_str
        for agente in los_agentes:
            agente.cleanup_test()
        wait_until_finished(los_agentes)

        Logger.printv()
        test = test.next()

    # Final cleanup
    Logger << "Final cleanup after all tests ..."
    for agente in los_agentes:
        agente.final_test_cleanup()
    # Wait for final cleanup to finish
    wait_until_finished(los_agentes)

    #-------------EXIT----------------

    Logger.printv()

    for agente in los_agentes:
        agente.request_client_exit()

    client.closeConnection()
    Logger << 'Subsystem connection closed.'

    time.sleep(1)
    killChildren()
    time.sleep(1)

    while client.anzahl_threads > 0:
        pass
    Logger.printv()
    Logger << 'ciao!'
    try:
        os.stat(Directories['logDir'])
    except:
        raise Exception("Couldn't find logDir %s"%Directories['logDir'])
    killChildren();

    del Logger
    #todo
    for Testboard in los_agentes[0].Testboards:
            try:
                dest = Testboard.parentDir+'logfiles'
                copytree(Directories['logDir'],dest)
                dest = Testboard.parentDir+'/configfiles/'
                if not os.path.exists(dest):
                    os.mkdir(dest)
                shutil.copy2(iniFile,dest)
                shutil.copy2(configFile,dest)
            except:
                raise
                #raise Exception('Could not copy Logfiles into testDirectory of Module %s\n%s ---> %s'%(Testboard.module,Directories['logDir'],Testboard.parentdir))
    try:
        rmtree(Directories['logDir'])
    except:
        pass
    #cleanup
    for Testboard in los_agentes[0].Testboards:
        try: rmtree(Testboard.parentDir+'/tmp/')
        except: pass
    #create tar.gz files
    for Testboard in los_agentes[0].Testboards:
        tarFileName = Testboard.parentDir
        if tarFileName.endswith('/'):
            tarFileName=tarFileName[:-1]
        tarFileName += '.tar.gz'
        tar = tarfile.open(tarFileName, "w:gz")
        tar.add(Testboard.parentDir, arcname=Testboard.moduleDir);
#        for name in ["file1", "file2", "file3"]:
#    tar.add(name)
        tar.close()
        pass
    #copy files to server
    checkConfig = config.has_option('Transfer','host')
    checkConfig = checkConfig and config.has_option('Transfer','port')
    checkConfig = checkConfig and config.has_option('Transfer','user')
    checkConfig = checkConfig and config.has_option('Transfer','destination')
    if  checkConfig:
        host = config.get('Transfer','host')
        port = config.get('Transfer','port')
        user = config.get('Transfer','user')
        dest = config.get('Transfer','destination')
        ssh = paramiko.SSHClient()
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host,port,username=user)
            transport = ssh.get_transport()
            ssh_client = scp.SCPClient(transport)
            if not dest.endswith('/'):
                dest+='/'
            for Testboard in los_agentes[0].Testboards:
                try:
                    tarFileName = Testboard.parentDir
                    if tarFileName.endswith('/'):
                        tarFileName=tarFileName[:-1]
                        tarFileName += '.tar.gz'
                    print 'copy file: %s --> %s:%s' % (tarFileName, host,dest)
                    try:
                        ssh_client.put(tarFileName, dest, preserve_times=True)
                    except scp.ScpError, e:
                        raise notch.agent.errors.DownloadError(str(e))
                except:
                    pass
        except:
            raise
    
except:
    killChildren()
    raise
    sys.exit(0)
