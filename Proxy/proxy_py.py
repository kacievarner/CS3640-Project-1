import socket
import sys
import os

# Since the server might send the HTML across more than one 
# send, we should try multiple recv calls to receive all data
def recvall(sock):
    BUFFER_SIZE = 4096 # 4 KiB
    data = b""
    while True:
        part = sock.recv(BUFFER_SIZE)
        data += part
        # Keep receiving only until the received data "ended" in last recv
        if len(part) < BUFFER_SIZE:
            break
    return data

# Create a server socket, bind it to a port and start listening
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverPort = 65534
listener.bind(('', serverPort))
listener.listen(1)
print('Ready to serve...')

while True:
    # accept a connection from the client side and decode the message/request
    clientSide, addr = listener.accept()
    message = clientSide.recv(1024).decode()
    # for now, lets ignore all the requests that are not GET
    # the remaining requests will just be discarded and the client 
    # will receive no response for those requests
    if not message.startswith("GET"):
        continue

    # extract the URL, domain, method, path from the request 
    request_method = message.split()[0]
    requested_url = message.split()[1]
    domain = requested_url.split("/", 3)[2]
    path = requested_url.split("/", 3)[3]

    # if the path ends in / then we can name it as index.html since 
    # is usually the case across the web
    if path == "":
        path = "index.html"
    print("request method: {}, requested URL: {} -> domain: {}, path: {}".format(request_method, requested_url, domain, path))
    
    # create the directory structure similar to how the paths
    # are defined within the URL. So, the parent folder will be the
    # domain you are visiting and the path will be converted into
    # subdirectories within the parent folder for intuitive navigation
    file_path = "./{}/{}".format(domain, path)
    file_exists = os.path.exists(file_path)

    if file_exists:
        # if the file exists, we can just read it and send it
        print("file was found in the local cache at the proxy")
        f = open(file_path, "rb")
        outputdata = f.read()
    else:
        # otherwise, we need to make the request to the remote server
        # to retrieve the file and send it to client while also saving
        # it locally for future visits
        print("file was NOT found in the local cache at the proxy")
        print("requesting from server...")

        # the GET request is made on HTTP/1.0 so that we don't need to 
        # deal with gzip compression and the response handling is fairly
        # straightforward
        GET_request = ""
        GET_request += "GET {} HTTP/1.0\r\n".format(requested_url)
        GET_request += "Host: {}\r\n\r\n".format(domain)
        print(GET_request)

        # we open the socket to the server and make the request at port 80
        serverSide = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSide.connect((domain, 80))

        # using the port you have created above to send the GET request
        serverSide.send(GET_request.encode())  

        # receive the response using recvall in case the response takes more 
        # than one send by the server to send
        GET_response = recvall(serverSide)
        print("R: {}".format(GET_response))

        # we create the directory and subdirectories in case they don't 
        # don't exist already and save the response as a file there
        file_dir = file_path.rsplit("/", 1)[0]
                
        # Added this if condition (thanks to Evan Jacobs) 
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        with open(file_path, "wb") as f:
            f.write(GET_response)

        # we are also going to send this response to the client
        outputdata = GET_response

    # send the outputdata (GET response) back to the client
    clientSide.send(outputdata)
    print("data sent")

listener.close()
