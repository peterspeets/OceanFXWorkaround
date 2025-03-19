import sys
import os
import copy
import numpy as np
import struct
import time
import usb.core
import usb.util
import usb.backend
import usb.backend.libusb1
import winsound

from spectrometer import *


class PyUSBSpectrometer(Spectrometer):
    
    def __init__(self, pathToUSBBackend = 'C:\\Program Files\\libusb-1.0.24\\MinGW64\\dll\\', idVendor=0x2457, idProduct=0x2001):
    
        """
        
        This script is a workaround for the Ocean Optics FX spectrometer. The memory chip that allows this specrometer
        to be faster than other Ocean spectrometers, does (in 2021) not always work with the provided Omnidriver.
        
        This script accesses the spectrometer with the usb python package and the libusb backend.
        
        Obtain a specrum with intensities(), and obtain a burst of spectra with burst(self, acquireNumberOfSpectra, dtype = np.float64), 
        with acquireNumberOfSpectra the number of spectra. burst() should use the onboard memory chip.
        """
    
        
        # If pyUSB still does not recognise libUSB, try put it in System32.
        if(pathToUSBBackend not in sys.path):
            sys.path.append(pathToUSBBackend)
            

        print('Looking for connected spectrometers:')
        
        try:
            self._spectrometer = usb.core.find(idVendor=idVendor, idProduct=idProduct)
            backend = None
        except Exception as e:
            print(e, ', attempting with hardcoded locaton for the DLL file.')
            backend = usb.backend.libusb1.get_backend(find_library = lambda x: 'C:\\Users\\pnaspeets\\octviewer\\libusb-1.0.24\\MinGW64\\dll\\libusb-1.0.dll')
            print(backend)
            try:
                self._spectrometer = usb.core.find(backend=backend, idVendor=idVendor, idProduct=idProduct)
            except:
                print('No local backend found: ', e)
        
        if(self._spectrometer is None):
            print('Spectrometer with id: ' , idProduct, ' not found.')
            self._spectrometer = usb.core.find(idVendor=idVendor)
        serialNumber = str(self._spectrometer.serial_number)
        usb.util.dispose_resources(self._spectrometer)
        
        time.sleep(0.1)    

        if(serialNumber ==  'OFX01948' ):
            import seabreeze.spectrometers as sb
            for i in range(15):
                try:
                    _spectrometer = sb.Spectrometer.from_first_available()
                    break
                except:
                    time.sleep(1)                
                    if(i == 10):
                        print('Cannot connect to USB spectrometer.')
                
            self._wavelengths = _spectrometer.wavelengths()
            _spectrometer.close()
        else:
            raise NotImplementedError("For some reason the old spectrometer does not work with USB commands.")
        
        time.sleep(0.1)
        if(backend is None):
            self._spectrometer = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        else:
            self._spectrometer = usb.core.find(backend = backend, idVendor=idVendor, idProduct=idProduct)
        if(self._spectrometer is None):
            try:
                self._spectrometer = usb.core.find(idVendor=idVendor)
            except Exception as e:
                print(e)
                self._spectrometer = usb.core.find(backend = backend, idVendor=idVendor)
        
            
        self._spectrometer.set_configuration()
         
        self._commands = {'reset'                       : b'\x00\x00\x00\x00', 
                        'getSerialNumber'               : b'\x00\x01\x00\x00', 
                        'isBuffering'                   : b'\x00\x08\x10\x00',
                        'setBuffering'                  : b'\x10\x08\x10\x00',
                        'getMaximumBufferSize'          : b'\x20\x08\x10\x00',
                        'getBufferSize'                 : b'\x22\x08\x10\x00',
                        'clearBuffer'                   : b'\x30\x08\x10\x00',
                        'setBufferSize'                 : b'\x32\x08\x10\x00',
                        'getNumberInBuffer'             : b'\x00\x09\x10\x00',
                        'getSpectra'                    : b'\x80\x09\x10\x00',
                        'getSingleSpectrum'             : b'\x00\x10\x10\x00',
                        'getIntegrationTime'            : b'\x00\x00\x11\x00',
                        'getMinimumIntegrationTime'     : b'\x01\x00\x11\x00',
                        'getMaximumIntegrationTime'     : b'\x02\x00\x11\x00',
                        'setIntegrationTime'            : b'\x10\x00\x11\x00',
                        'getTrigger'                    : b'\x00\x01\x11\x00',
                        'getNumberOfSpectraPerTrigger'  : b'\x02\x01\x11\x00',
                        'setTriggerMode'                : b'\x10\x01\x11\x00',
                        'setNumberOfSpectraPerTrigger'  : b'\x12\x01\x11\x00',
                        'getNumberOfPixels'             : b'\x20\x02\x11\x00'
                        }
        
        self._errorMessages = {0 :  'Success', 
                            1 :  'Bad Protocol',
                            2 :  'Bad Message',
                            3 :  'Bad Checksum',    
                            4 :  'Message Too Large',  
                            5 : 'Invalid Payload Length',  
                            6 :  'Invalid Payload Data',  
                            7 :  'Device Not Ready',  
                            8 : 'Unknown Checksum Type',  
                            9  : 'Device Reset',  
                            10 :  'Too Many Buses',  
                            11  : 'Out of Memory', 
                            12 :  'Value Not Found',    
                            13 :  'Device Fault', 
                            14 :  'Bad Footer', 
                            15 :  'Request Interrupted', 
                            16 :  'I/O Error',
                            100 :  'Bad Cipher', 
                            101 :  'Bad Firmware',
                            102 :  'Incorrect Packet Length'
                            }
         

        print('Setting trigger and exposure time.')
        self.triggerMode(0)
        self.setIntegrationTime(self.getMinimumIntegrationTime())
        self.setBuffering(False)
        
        print('Spectrometer test: ', end='')
        spectrum = self.intensities()
        self._deadTime = -999
        testResult = False
        
        if(len(spectrum) == self.getNumberOfPixels() and np.any(spectrum > 0)):
            try:
                self.burst(500)
            except:
                testResult = False
            
            print('Spectrometer dead time: ', self._deadTime)
            if(self._deadTime != -999):
                testResult = True
            else:
                testResult = False
                    
        else:
            testResult = False
        if(testResult):
            print('Test passed.')
        else:
            print('Test failed.')
                            
                              
 
    def intensities(self):
        answer = self._query('getNumberOfPixels')
        numberOfPixels = struct.unpack('<H',answer[24:26])[0]
        spectrum = np.empty(numberOfPixels)        
        answer = self._query(self._commands['getSingleSpectrum'])      
        
        
        payload = answer[44:-20]
        iterator = struct.iter_unpack('<H',payload)
        

        for i in range(len(payload)//2):
            spectrum[i] = next(iterator)[0]
        if(len(spectrum) < numberOfPixels or len(answer) < 128):
            time.sleep(0.01)
            print('Device blocked. Retrying: ')
            return self.intensities()
        return spectrum
        
        
    def reset(self):
        self._query('reset')
        
    def getDeadTime(self):
        return self._deadTime    
        
    def setIntegrationTime(self, integrationTime):
        message = struct.pack('<I', integrationTime)
        self._query('setIntegrationTime', message = message)

        
    def getIntegrationTime(self):
        answer = self._query('getIntegrationTime')
        return struct.unpack('<I', answer[24:28])[0]    
    
           
    @property
    def integrationTimeLimits(self):
        """
        get minimum and maximum integration time from spectrometer.
        """
        
        return (self.getMinimumIntegrationTime(), 
                self.getMaximumIntegrationTime())
                
    
    def getMaximumIntegrationTime(self):
        answer = self._query('getMaximumIntegrationTime')
        return struct.unpack('<I', answer[24:28])[0]    
    
    def getMinimumIntegrationTime(self):
        answer = self._query('getMinimumIntegrationTime')
        return struct.unpack('<I', answer[24:28])[0]    
    
    def getSerialNumberBytes(self):
        answer = self._query('getSerialNumber')
        return answer[24:40]  
        
        
    def getMaximumBufferSize(self):
        answer = self._query('getMaximumBufferSize')
        return struct.unpack('<I', answer[24:28])[0]

    def getBufferSize(self):
        answer = self._query('getBufferSize')
        return struct.unpack('<I', answer[24:28])[0]
        
    def getNumberInBuffer(self):
        answer = self._query('getNumberInBuffer')
        return struct.unpack('<I', answer[24:28])[0]    
        
        
        
        
    def getNumberOfPixels(self):
        answer = self._query('getNumberOfPixels')
        #strictly speaking this is undefined behaviour, since spectrometer sends a U16, and not a U32.
        return struct.unpack('<I', answer[24:28])[0]
        
    def softwareTrigger(self):
        """
        The spectrometer only starts buffering after a trigger.
        This trigger can be a request for spectra. According
        to the manual, asking form an empty buffer should give
        a message with 0 spectra. However, this throws an error 13. It
        works though.
        """
        
        self.getRawSpectra(0)
  
   
   
    def getRawSpectra(self, maxNumberOfSpectra = 15):
        """
        This method is as a discount. It gives UP TO the number of 
        requested spectra. 15 is the amount recommended by the
        manual. They claim 15 gives per request gives the highest
        throughput.
        """
        
        spectraInBuffer = self.getNumberInBuffer()
        getSpectra = np.amin([spectraInBuffer, maxNumberOfSpectra])
        
        message = struct.pack('<I', getSpectra)        
        byteSpectra = self._query('getSpectra', message = message)
        return self._processRawSpectalData(byteSpectra)
        
   
        
    def isBuffering(self):
        answer = self._query('isBuffering')
        return struct.unpack('<?', answer[24:25])[0]  
        
    def setBuffering(self, value):
        message = struct.pack('<?', value)
        self._query('setBuffering', message = message)
        
        
    def setBufferSize(self, bufferSize):
        bufferSize = np.amin([self.getMaximumBufferSize(), bufferSize])
        message = struct.pack('<I', bufferSize)
        self._query('setBufferSize', message = message)

    def clearBuffer(self):
        self._query('clearBuffer')
        
        
    def setNumberOfSpectraPerTrigger(self, numberOfSpectra):
        message = struct.pack('<I', numberOfSpectra)
        self._query('setNumberOfSpectraPerTrigger', message = message)
        
    def getNumberOfSpectraPerTrigger(self):
        answer = self._query('getNumberOfSpectraPerTrigger')
        return struct.unpack('<I', answer[24:28])[0]            


    def triggerMode(self, triggerMode):
        """
        This function the triggering behaviour can be changed. Trigger mode can be 0-4.
        0: Continuous acquisition. The spectrometer will always measure and will just
        give a spectrum it measued when asked. This means spectrum retrieval time varies.
        This is the setting (setting 0) you want.
        1: software tiggering.
        2: external synchronisation
        3: hardware triggering
        4: single shot. Tbe spectrometer will only measure once getSpectum is called. 
        you have to listen very carfully, because the spectrometer will measure only once.
        Until another call to getSpectrum is made.
        """
        

        message = struct.pack('<I', triggerMode)
        self._query('setTriggerMode', message = message)
        
        








    def burst(self, acquireNumberOfSpectra, dtype = np.float64):
        startTime = time.time()
    
        bufferSize = 50000
        maximumChunkSize = 15
        
        
        self.triggerMode(0)
        
        self.setBuffering(True)
        self.clearBuffer()
        integrationTime = self.getIntegrationTime()
        spectrumLength = self.getNumberOfPixels()
        

        
        
        if(not self.isBuffering()):
            print('A problem has occured with the buffer.')        
        self.setBufferSize(bufferSize)
        if(self.getBufferSize() != bufferSize):
            print('Could not create buffer space. Requested buffer space: {}, currently: {}'.format(bufferSize, self.getBufferSize()))        
        self.setNumberOfSpectraPerTrigger(bufferSize)
    
        

            
        
        headers = np.array([{} for i in range(acquireNumberOfSpectra)])
        spectra = np.empty((acquireNumberOfSpectra, spectrumLength ),dtype=dtype)
        
        
        chunkSize = np.amin([acquireNumberOfSpectra,maximumChunkSize])

        
        acquiredSpectra = 0
        

        #print('Please disregard any ERROR 13 until stated otherwise. This does not guarantee there is no ERROR 13, but an ERROR 13 will be always thrown here. If the spectrometer hangs, there probably was an ERROR 13.')

        self.softwareTrigger()
            #print('If there is any ERROR 13 from now on, there really is an ERROR 13.')
        
        
        self.stopBurst = False
        self.clearBuffer()
        startLoop = True
        while(acquiredSpectra < acquireNumberOfSpectra):
            inBuffer = self.getNumberInBuffer()
            if( (acquireNumberOfSpectra - acquiredSpectra) < chunkSize):
                chunkSize = (acquireNumberOfSpectra - acquiredSpectra)
                
            if(startLoop):
                self.clearBuffer()
                startLoop = False
            while(self.getNumberInBuffer() < chunkSize  ):
                time.sleep(1e-6 * integrationTime )
            
            chunkHeaders, chunkSpectra = self.getRawSpectra(chunkSize)
            headers[acquiredSpectra:acquiredSpectra+chunkSize] = chunkHeaders
            spectra[acquiredSpectra:acquiredSpectra+chunkSize] = chunkSpectra
            acquiredSpectra += chunkSize
            if(acquiredSpectra % 1000 == 0):
                print('{} spectra acquired in {} s. {} in buffer.'.format(acquiredSpectra,time.time() - startTime, self.getNumberInBuffer()))
            if(self.stopBurst):
                self.stopBurst = False
                break
        
        if(len(headers) > 1 and 'timeStamp' in headers[0] and 'timeStamp' in headers[-1]):
            t0 = headers[0]['timeStamp']
            t1 = headers[-1]['timeStamp']
        else:
            t0 = -999
            t1 = 999
        
        dt = 1e-3*(t1 - t0)/acquiredSpectra
        self._deadTime = 1e3*dt - integrationTime # in us
        totalTime = time.time() - startTime
        print('{} spectra acquired in {:.4f} s.  Per spectrum T =  {:.4f} ms. {:.4f} kHz. (overhead is {:.4f} s)'.format(acquiredSpectra, totalTime, dt, 1/dt, totalTime - acquiredSpectra*dt*1e-3  ))
        print('Dead time: {:.4f} us'.format(self._deadTime))  
        if(len(headers) > 2 and self._deadTime > 211.12455):
            delays = np.diff([h['timeStamp'] for h in headers])
            
            mint = np.amin(delays)
            maxt = np.amin(delays)
            minIndex = np.argmin(delays)
            maxIndex = np.argmax(delays)
            print('Large dead time {:.1f}. Largest difference between time stamps: {}.'.format(self._deadTime, maxt-mint))
            
            if(maxt- mint > 2 ):
               
                print('\n\n\nUNEXPECTED TIME STAMP. Integation time changed, or spectrum skipped. Check buffer overflow.\n\n')
                print('Unexpected time delay. Min Delta t ({}): {:.2f}, max Delta t ({}): {:.2f}'.format(minIndex, mint,maxIndex, maxt))
                print('Difference: ', maxt- mint)
                print('\n\n')
                winsound.Beep(1047, 63) 
                winsound.Beep(1047, 63) 
                winsound.Beep(1047, 63) 
                winsound.Beep(1047, 63)
            
        
        
        self.clearBuffer()
        self.setBuffering(False)
        
        return headers, spectra
               

        
        
    def _query(self, query, message = 0, writeEndpoint = 0x01, readEndpoint = 0x81):
        if(type(query) == str):
            messageType = self._commands[query]
        else:
            messageType = query
        
        answer =  self._queryPyUSB(messageType, message = message, writeEndpoint = writeEndpoint, readEndpoint = readEndpoint)
        
        if(answer[6:8] != b'\x00\x00'):
            errorCode = struct.unpack('<H', answer[6:8])[0]
            if(errorCode in self._errorMessages):
                errorMessage = self._errorMessages[errorCode]
            else:
                errorMessage = ''
            print('ERROR: '.format(errorMessage, errorCode) )
            command = answer[8:12]
            commandString = ''
            
            if(errorMessage == ''):
                print('Unrecoverable error. Device will reset.')
                self.reset()
            
            for c in self._commands:
                if(self._commands[c] == command):
                    commandString = c
            print('Problem with command: {} CODE {} '.format(commandString, command))
            
        return answer
    

    def _queryPyUSB(self, messageType, message = 0, writeEndpoint = 0x01, readEndpoint = 0x81):

        if(type(message) == int):
            message = struct.pack('<I', message)
        elif(message is None):
            message = b''
        message = self.makeOBPMessage(message, messageType)
        self._spectrometer.write(writeEndpoint,message, 100)
        response = self._spectrometer.read(readEndpoint, 100)
        response = response.tobytes()
        remainingBytes = struct.unpack('<I', response[40:44])[0] - 20
        if(remainingBytes > 0):
            response = response +  self._spectrometer.read(readEndpoint, remainingBytes).tobytes()
        
        if(response[6:8] != b'\x00\x00'):
            print('ERROR CODE: ', struct.unpack('<H', response[6:8])[0] )
            print('Problem with command: ', response[8:12] )
            if(messageType != response[8:12] ):
                print('Problem with command: ', messageType)
        return response
            
    
    

    @staticmethod
    def _parseRawSpectrum(rawByteString):
        header = {}
        
        dataFormats = ['U16', 'U24', 'U32', 'SPFP'] #unsigned integer 16, 24, 32. single precision floating point.
        bytesPerDatapoints = [2,3,4,8]
        header['protocol'] = struct.unpack('<H', rawByteString[0:2])[0]
        header['metaDataLengthBytes'] = struct.unpack('<H', rawByteString[2:4])[0]
        if(header['metaDataLengthBytes'] != 64):
            print('Unexpected metadata length.')
        header['spectrumLength'] = struct.unpack('<I', rawByteString[4:8])[0]
        header['timeStamp'] = struct.unpack('<Q', rawByteString[8:16])[0]
        header['integrationTime'] = struct.unpack('<I', rawByteString[16:20])[0]
        header['pixelDataFormatCode'] = struct.unpack('<I', rawByteString[20:24])[0]
        header['pixelDataFormat'] = dataFormats[header['pixelDataFormatCode']-1]
        header['bytePerDatapoint'] = bytesPerDatapoints[header['pixelDataFormatCode']-1]
        header['spectrumIndex'] = struct.unpack('<I', rawByteString[24:28])[0]
        # index of spectrum that is measured when this spectrum was grabbed from the spectrometer
        header['lastSpectrumIndex'] = struct.unpack('<I', rawByteString[28:32]) [0]
        header['timeStampLastSpectrum'] = struct.unpack('<Q', rawByteString[32:40])[0]# heuristic for grabbing (not measuring time, but the time at grab.) time. Does not seem to work, though.
        header['numberOfAveraging'] = struct.unpack('<H', rawByteString[40:42])[0]
        header['spectrumLengthBytes'] = header['spectrumLength']
        
        header['spectrumLength'] //= header['bytePerDatapoint']
        

        
        if(header['pixelDataFormat'] == 'U16'):
            spectrum = np.empty(header['spectrumLength'], dtype = np.uint16)
            structFormat = '<H'    
        elif(header['pixelDataFormat'] == 'U24'):
            spectrum = np.empty(header['spectrumLength'], dtype = np.uint32) #no uint24
            structFormat = ''
        elif(header['pixelDataFormat'] == 'U32'):
            spectrum = np.empty(header['spectrumLength'], dtype = np.uint32)
            structFormat = '<H'
        elif(header['pixelDataFormat'] == 'SPFP'):
            spectrum = np.empty(header['spectrumLength'], dtype = float)
            structFormat = '<f'
        else:
            print('Data type not recognised.')
            
        if(structFormat == ''):
            for i in range(header['spectrumLength']):
                spectrum[i] = int.from_bytes(rawByteString[64:header['spectrumLengthBytes']+64][3*i:3*i+3],'little',signed=False)
        else:
            iterator = struct.iter_unpack(structFormat,rawByteString[64:header['spectrumLengthBytes']+64])
            for i in range(header['spectrumLength']):
                spectrum[i] = next(iterator)[0]                
        return header, spectrum


    
    def _processRawSpectalData(self, byteString):
        if(byteString[0] == 193 and byteString[1] == 192):
            byteString = byteString[44:-24]
        spectra = []
        headers = []
        
        while(len(byteString) > 0):
            
            if(len(byteString) < 129 and len(byteString) > 0 ):
                print('Groot probleem. ', len(byteString) )
                break
            else:
                header, spectrum = self._parseRawSpectrum(byteString)
                headers.append(header)
                spectra.append(spectrum)

                byteString = byteString[header['metaDataLengthBytes'] +header['spectrumLengthBytes']+4: ]    
        return headers, spectra


    @staticmethod
    def makeOBPMessage(message, messageType,requestAck = True):

        startBytes = b'\xC1\xC0'
        protocolVersion = b'\x00\x00'
        if(requestAck):
            flag = struct.pack('<BB',4,0)
        else:
            flag = b'\x00\x00'
        errorNumber =  b'\x00\x00'
        messageType = messageType
        regarding = struct.pack('<I', 0)
        reserved = b'\x00\x00\x00\x00\x00\x00'
        checksumType = b'\x00'
        if(len(message) > 16):
            immediateDataLength = b'\x00'
            immediateData =  struct.pack('<IIII', 0,0,0,0)
            bytesRemaining = struct.pack('<I', 20 + len(message))
            payload = message
        else:
            immediateDataLength = struct.pack('<B', len(message))
            immediateData =  message.ljust(16, b'\x00')
            bytesRemaining =  struct.pack('<I', 20)
            payload = b''
            
        checksum = struct.pack('<IIII', 0,0,0,0)
        footer = b'\xC5\xC4\xC3\xC2'



        messageBytes = (startBytes + 
                        protocolVersion + 
                        flag + 
                        errorNumber +
                        messageType + 
                        regarding + 
                        reserved + 
                        checksumType + 
                        immediateDataLength + 
                        immediateData + 
                        bytesRemaining + 
                        payload + 
                        checksum + 
                        footer)
        return messageBytes
    
    def wavelengths(self):
        return self._wavelengths
