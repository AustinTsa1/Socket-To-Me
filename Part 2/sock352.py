
# CS 352 project part 2 
# this is the initial socket library for project 2 
# You wil need to fill in the various methods in this
# library 

# main libraries 
import binascii
import socket as syssock
import struct
import sys

# encryption libraries 
import nacl.utils
import nacl.secret
import nacl.utils
from nacl.public import PrivateKey, Box

# if you want to debug and print the current stack frame 
from inspect import currentframe, getframeinfo

# supports my own testing for dropped packets
import random

transmitter = -1
receiver = -1
mainSocket = (0,0)
otherHostAddress = ""
currentSeqNo = 0
sock352PktHdrData = "!8BLLBB"
#each one of these are represented as a B
version = 0x1
protocol = 0x0
checksum = 0x0
source_port = 0x0
dest_port = 0x0
window = 0x0
header_len = 18
deliveredData = ""

"""
Flag Name       (Hex) Value     (Binary) Value  (Binary) Meaning
SOCK352_SYN     0x01            00000001        Connection initiation
SOCK352_FIN     0x02            00000010        Connection end
SOCK352_ACK     0x04            00000100        Acknowledgement #
SOCK352_RESET   0x08            00001000        Reset the connection
SOCK352_HAS_OPT 0xA0            00010000        Option field is valid
"""

# these are globals to the sock352 class and
# define the UDP ports all messages are sent
# and received from

# the ports to use for the sock352 messages 
global sock352portTx
global sock352portRx
# the public and private keychains in hex format 
global publicKeysHex
global privateKeysHex

# the public and private keychains in binary format 
global publicKeys
global privateKeys

# the encryption flag 
global ENCRYPT

publicKeysHex = {} 
privateKeysHex = {} 
publicKeys = {} 
privateKeys = {}

# this is 0xEC 
ENCRYPT = 236 

global communication_box
global my_secret_key
global other_host_public_key
global default_secret_key
global default_public_key

my_secret_key = -1
other_host_public_key = -1
default_secret_key = -1
default_public_key = -1

# this is the structure of the sock352 packet 
#sock352HdrStructStr = '!BBBBHHLLQQLL'

# this init function is global to the class and
# defines the UDP ports all messages are sent
# and received from.
def init(UDPportTx,UDPportRx):
    global mainSocket, transmitter, receiver

    # create a UDP/datagram socket 
    # bind the port to the Rx (receive) port number
    mainSocket = syssock.socket(syssock.AF_INET, syssock.SOCK_DGRAM)
    receiver = int(UDPportRx)
    if(UDPportTx == ''):
        transmitter = receiver
    else:
        transmitter = int(UDPportTx)
    mainSocket.bind( ('', receiver) )
    # Our protocol defines a timeout of 0.2 seconds
    mainSocket.settimeout(0.2)
    print('Initialization complete!')
    return

    
# read the keyfile. The result should be a private key and a keychain of
# public keys
def readKeyChain(filename):
    global publicKeysHex, privateKeysHex, publicKeys, privateKeys
    global default_secret_key, default_public_key
    
    if (filename):
        try:
            keyfile_fd = open(filename,"r")
            for line in keyfile_fd:
                words = line.split()
                # check if a comment
                # more than 2 words, and the first word does not have a
                # hash, we may have a valid host/key pair in the keychain
                if ( (len(words) >= 4) and (words[0].find("#") == -1)):
                    host = words[1]
                    port = words[2]
                    keyInHex = words[3]
                    if (words[0] == "private"):
                        privateKeysHex[(host,port)] = keyInHex
                        privateKeys[(host,port)] = nacl.public.PrivateKey(keyInHex, nacl.encoding.HexEncoder)
                        if(host == '*' and port == '*'):
                            default_secret_key = privateKeys[(host,port)]
                    elif (words[0] == "public"):
                        publicKeysHex[(host,port)] = keyInHex
                        publicKeys[(host,port)] = nacl.public.PublicKey(keyInHex, nacl.encoding.HexEncoder)
                        if(host == '*' and port == '*'):
                            default_public_key = publicKeys[(host,port)]
        except Exception,e:
            print ( "error: opening keychain file: %s %s" % (filename,repr(e)))
    else:
        print ("error: No filename presented")             
    """
    print ("These are the PUBLIC keys obtained:")
    for public_address in publicKeys:
        print ("%s\t\t:\t%s"% (public_address,publicKeysHex[public_address]) )
    print ("These are the PRIVATE keys obtained:")
    for private_address in privateKeys:
        print ("%s\t\t:\t%s"% (private_address,privateKeysHex[private_address]) )
    """
    return (publicKeys,privateKeys)

class socket:
    
    def __init__(self):
        print("\tReturning your new 352-socket!")
        return 
        
    def bind(self,address):
        # bind is not used in this assignment 
        return

    def connect(self,*args):

        global sock352portTx, ENCRYPT, mainSocket, currentSeqNo, communication_box, receiver
        global publicKeys, default_public_key, other_host_public_key, my_secret_key, default_secret_key

        # Store the (host,port) tuple in a single variable
        address = []
        # example code to parse an argument list 
        if (len(args) >= 1): 
            address = args[0]
        if (len(args) >= 2):
            if (args[1] == ENCRYPT):
                self.encrypt = True
                for private_address in privateKeys:
                    print("\tComparing ",private_address,"\tto  localhost,",receiver)
                    if(private_address == ('localhost',receiver)):
                        my_secret_key = privateKeys[private_address]
                        break
                if(my_secret_key == -1):
                    my_secret_key = default_secret_key
                if(my_secret_key == -1):
                    print("\tERROR. NO PRIVATE KEY FOUND FOR THIS HOST. TERMINATING.")
                    return
            else:
                print ("\tInvalid encryption flag! Self-destructing now . . .")
                return
                
        print("\tInitiating a conection on %s" % (transmitter) )
        
        #  create a new sequence number
        currentSeqNo = int( random.randint(20, 100) )
        #  create a new packet header with the SYN bit set in the flags
        #  (use the Struct.pack method)
        #  also set the other fields (e.g sequence #)
        header = self.__make_header(0x0,0x01, currentSeqNo, 0, 0)
        ackFlag = -1
        #   set the timeout
        #      wait for the return SYN
        #        if there was a timeout, retransmit the SYN packet
        while(ackFlag != currentSeqNo ):
            print("\tRequesting a new connection...%d bytes sent!" % (mainSocket.sendto(header,
                (address[0], transmitter) ) ) )
            newHeader = self.__sock352_get_packet()
            ackFlag = newHeader[9]
        # We are safe to establish this UDP connection to the other host
        mainSocket.connect( (address[0], transmitter) )
        # Establish the encryption keys and box
        for public_address in publicKeys:
            if(public_address == (address[0], transmitter) ):
                other_host_public_key = publicKeys[public_address]
        if(other_host_public_key == -1):
            other_host_public_key = default_public_key
        if(other_host_public_key == -1):
            print("\tERROR. NO PUBLIC KEY FOUND FOR THE OTHER HOST. TERMINATING.")
            return
        print("\tI think my secret key is %s and their public key is %s" % (my_secret_key, other_host_public_key))
        communication_box = Box(my_secret_key,other_host_public_key)
        #   set the sequence number of the upcoming data to send
        currentSeqNo += 1
        return

    def listen(self,backlog):
        # listen is not used in this assignments 
        pass
    
    def accept(self,*args):
        global ENCRYPT, mainSocket, receiver, currentSeqNo, communication_box, receiver
        global publicKeys, default_public_key, other_host_public_key, my_secret_key, default_secret_key

        # example code to parse an argument list 
        if (len(args) >= 1):
            if (args[0] == ENCRYPT):
                self.encryption = True
                for private_address in privateKeys:
                    print("\tComparing ",private_address,"\tto  localhost,",receiver)
                    if(private_address == ('localhost',receiver)):
                        my_secret_key = privateKeys[private_address]
                        break
                if(my_secret_key == -1):
                    my_secret_key = default_secret_key
                if(my_secret_key == -1):
                    print("\tERROR. NO PRIVATE KEY FOUND FOR THIS HOST. TERMINATING.")
                    return
            else:
                print ("\tInvalid encryption flag! Self-destructing now . . .")
                return
        
        print('\tWe are waiting for a connection on %s\n' % (receiver) )
        flag = -1
        newHeader = ""
        # call  __sock352_get_packet() until we get a new connection
        while(flag != 0x01):
            newHeader = self.__sock352_get_packet()
            flag = newHeader[1]
        currentSeqNo = newHeader[8]
        #Acknowledge this new connection
        header = self.__make_header(0x0,0x04,0,currentSeqNo,13)
        mainSocket.sendto(header+"I accept you.", otherHostAddress)
        # Establish the encryption keys and box
        for public_address in publicKeys:
            if(public_address == otherHostAddress ):
                other_host_public_key = publicKeys[public_address]
        if(other_host_public_key == -1):
            other_host_public_key = default_public_key
        if(other_host_public_key == -1):
            print("\tERROR. NO PUBLIC KEY FOUND FOR THE OTHER HOST. TERMINATING.")
            return
        print("\tI think my secret key is %s and their public key is %s" % (my_secret_key, other_host_public_key))
        communication_box = Box(my_secret_key,other_host_public_key)
        #
        # Get ready to expect new data packets
        currentSeqNo += 1
        print("\tAcquired a connection! Calling new init...")
        clientsocket = socket()
        return (clientsocket,otherHostAddress)

    def close(self):
        # send a FIN packet (flags with FIN bit set)
        print("\tClosing the connection")
        # Make a new header with a random seq_no
        terminal_no = random.randint(7,19)
        header = self.__make_header(0x0,0x02, terminal_no, 0, 0)
        ackFlag = -1
        #   set the timeout
        #      wait for acknowledgement
        #        if there was a timeout, retransmit the FIN packet
        while(ackFlag != terminal_no):
            try:
                mainSocket.sendto(header, otherHostAddress)
            except TypeError:
                mainSocket.send(header)
            newHeader = self.__sock352_get_packet()
            ackFlag = newHeader[9]
        # We are safe to close this UDP connection with the other host
        mainSocket.close()

        # Note:
        # If the final ACK packet for the tear down gets dropped,
        # one host will close the connection and the other host
        # will forcibly lose its connection.
        return

    def send(self,buffer):
        global mainSocket, header_len, currentSeqNo, communication_box
        
        bytesSent = 0
        msglen = len(buffer)
        # make sure the correct fields are set in the flags
        # make sure the sequence and acknowlegement numbers are correct
        # create a new sock352 header using the struct.pack
        # create a new UDP packet with the header and buffer 
        # send the UDP packet to the destination and transmit port
        # set the timeout
        # wait or check for the ACK or a timeout
        print("\tStarting send!")
        while(msglen > 0):
            # Take the top 255 bytes of the message because that is the
            # maximum payload we can represent with a "B" in struct format
            # encryption introduces an extra 40 bytes of metadata
            parcel_len = 255
            optionBit = 0x0
            encryption_filler = 0
            parcel = ""
            if(self.encrypt):
                encryption_filler = 40
                parcel_len = 215
                parcel = buffer[:parcel_len]
                nonce = nacl.utils.random(Box.NONCE_SIZE)
                parcel = communication_box.encrypt(parcel, nonce)
                optionBit = 0x1
            else:
                parcel = buffer[:parcel_len]
            parcelHeader = self.__make_header(optionBit,0x03,currentSeqNo,0,parcel_len )
            tempBytesSent = 0
            ackFlag = -1
            print("About to send --- %s ---" % parcel)
            # Keep resending this packet until the proper ACK is received
            while(ackFlag != currentSeqNo):
                tempBytesSent = mainSocket.send(parcelHeader+parcel) - header_len - encryption_filler
                #print("\tSent sequnce number: %d" % currentSeqNo)
                newHeader = self.__sock352_get_packet()
                ackFlag = newHeader[9]
                #print("\t\tReceived this ack: %d" % ackFlag)
            # update the local variables to show that this last packet
            # was successfully sent
            msglen -= parcel_len
            buffer = buffer[parcel_len:]
            bytesSent += tempBytesSent
            currentSeqNo += 1
        print("\tOne segment of %d total bytes was sent!" % bytesSent)
        return bytesSent

    def recv(self,nbytes):
        global mainSocket, deliveredData, currentSeqNo
        
        print("\tStarted the recv() call!")
        deliveredData = ""
        # call __sock352_get_packet() to get packets (polling)
        # check the list of received fragements
        # copy up to nbytes into a buffer
        # return the buffer if there is some data
        fullMessage = ""
        while(nbytes > 0):
            seq_no = -1
            # Keep checking incoming packets until we receive one with
            # the sequence number we were expecting
            while(seq_no != currentSeqNo):
                newHeader = self.__sock352_get_packet()
                seq_no = newHeader[8]
                print("\tReceived sequence number %d" % seq_no)
                if(seq_no != currentSeqNo):
                    print("\tWe expected the sequence number %d, but didn't get it!" % currentSeqNo)
                # Acknowledge whatever it is we received
                header = self.__make_header(0x0,0x04, 0,seq_no,0)
                mainSocket.sendto(header, otherHostAddress)
            print("Just received --- %s ---" % deliveredData)
            if(newHeader[2] == 0x1):
                deliveredData = communication_box.decrypt(deliveredData)
            # The previous packet was the one we expected, so add its data to our buffer
            fullMessage += deliveredData
            nbytes -= len(deliveredData)
            # Get ready to expect the next packet
            currentSeqNo += 1
        print("\tFinished receiving the requested amount!")
        return fullMessage

    def  __sock352_get_packet(self):
        global mainSocket, sock352PktHdrData, otherHostAddress, deliveredData
        
        # Wait 0.2 seconds to receive a packet, otherwise return an empty header
        try:
            (data, senderAddress) = mainSocket.recvfrom(4096)
        except syssock.timeout:
            print("\t\tNo packets received before the timeout!")
            z = [0,0,0,0,0,0,0,0,0,0,0,0]
            return z
        
        # Randomly pretend this packet got dropped or corrupted
        """
        if(random.randint(1,3) == 2):
            print("\t\tIncoming packet got dropped! Timeout.")
            #z = self.__make_header(0x0,1,1,1,1)
            #print("\t\tAssembled this header: ")
            #print(z)
            z = [0,0,0,0,0,0,0,0,0,0,0,0]
            return z
        """
        # Separate the header and the message
        (data_header, data_msg) = (data[:18],data[18:])
        header = struct.unpack(sock352PktHdrData, data_header)
        flag = header[1]

        # Python lacks a switch statement!
        # Elif isn't so ugly...but still!

        #   First check if it's a connection set up (SYN bit set in flags)
        #    If so, save the address of the sender so the calling function
        #    can make use of it
        if(flag == 0x01):
            otherHostAddress = senderAddress
            return header
        #   if it is a connection tear down (FIN) 
        #   send a FIN packet
        elif(flag == 0x02):
            terminalHeader = self.__make_header(0x0,0x04,0,header[8],0)
            mainSocket.sendto(terminalHeader, senderAddress)
            return header
        #      else if it is a data packet
        #      save the message in a global variable so the calling
        #       function can make use of it
        elif(flag == 0x03):
            deliveredData = data_msg
            return header
        #   else if it is an ACK packet, let the calling function know
        elif(flag == 0x04):
            return header
        #   If we get a reset packet, ignore it. The calling function should
        #   handle the resend
        elif(flag == 0x08):
            return header
        #   else if it's nothing it's a malformed packet.
        #   send a reset (RST) packet with the sequence number
        else:
            header = self.__make_header(0x0,0x08,header[8],header[9],0)
            if(mainSocket.sendto(header,senderAddress) > 0):
                print("\t\tSent a reset packet!")
            else:
                print("\t\tFailed to send a reset packet!")
            return header
    
    def  __make_header(self, givenOption, givenFlag, givenSeqNo, givenAckNo, givenPayload):
        global sock352PktHdrData, header_len, version, protocol
        #TODO: figure out line breaks!
        global checksum, source_port, dest_port, window

        # For Part 1, these are the only flags that vary based on the type
        # of packet being sent, so we ask for them in the parameters
        # the rest aren't used and have been initialized globally
        opt_ptr = givenOption
        flags = givenFlag
        sequence_no = givenSeqNo
        ack_no = givenAckNo
        # TODO: payload length might be 40 bytes longer when encrypted
        payload_len = givenPayload
        # create a struct using the format that was saved globally
        udpPkt_hdr_data = struct.Struct(sock352PktHdrData)
        # pack this data into a struct and return it
        return udpPkt_hdr_data.pack(version, flags, opt_ptr, protocol,
            header_len, checksum, source_port, dest_port, sequence_no,
            ack_no, window, payload_len)
#end