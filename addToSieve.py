#!/usr/bin/python

import ConfigParser, os
import sievelib,time,getpass
from sievelib.managesieve import Client
from sievelib.parser import Parser
from sievelib.factory import FiltersSet
import imaplib, email

msgHeaders=['List-Id', 'From', 'Sender','Subject','To', 'X-Original-To', 'X-Envelope-From','X-Spam-Flag']
headers=["address","header"] 
keyWords={"address": ["From","To"],
	  "header":  ["subject","Sender","X-Original-To","List-Id"]
	}

def doFolderExist(folder,M):
	return (M.select(folder))

def selectAction(p,M): #header="", textHeader=""):
	i = 1
	for r in p.result:
		if r.children:
			if (type(r.children[0]) == sievelib.commands.FileintoCommand):
				print "%2d) Folder  %s" %(i,r.children[0]['mailbox'])
			elif (type(r.children[0]) == sievelib.commands.RedirectCommand):
				print "%2d) Address %s" %(i,r.children[0]['address'])
			else:
				print "%2d) Not implemented %s" %(i,type(r.children[0]))
		else:
			print "%2d) Not implemented %s" %(i,type(r))
			
		i = i + 1
	print "%2d) New folder "%i
	print "%2d) New redirection"%(i+1)
		


	option = raw_input("Select one: ")

	print option, len(p.result)

	actions=[]

	if (int(option) <= len(p.result)):
		action=p.result[int(option)-1].children

		for i in action:
			if i.arguments.has_key('mailbox'):
				actions.append(("fileinto",i.arguments['mailbox']))
			elif i.arguments.has_key('address'):
				actions.append(("redirect",i.arguments['address']))
			else:	
				actions.append(("stop",))
				
				
		print actions

		match=p.result[int(option)-1]['test']
		print "match ", match
	elif (int(option) == len(p.result)+1):
		folder= raw_input("Name of the folder: ")
		print "Name ", folder
		if (doFolderExist(folder,M)[0]!='OK'):
			print "Folder ",folder," does not exist"
			sys.exit()
		else:
			print "Let's go"
			actions.append(("fileinto", folder))
			actions.append(("stop",))
	elif (int(option) == len(p.result)+2):
		redir= raw_input("Redirection to: ")
		print "Name ", redir
		itsOK= raw_input("It's ok? (y/n)")
		if (itsOK!='y'):
			print redir," is wrong"
			sys.exit()
		else:
			print "Let's go"
			actions.append(("redirect", redir))
			actions.append(("stop",))

	return actions

def selectHeader():
	i = 1
	for j in headers:
		print i, ") ", j, "(", keyWords[headers[i-1]],")"
		i = i + 1
	return headers[int(raw_input("Select header: "))-1]
	
def selectKeyword(header):	
	i = 1
	for j in keyWords[header]:
		print i, ") ", j
		i = i + 1
	return keyWords[header][int(raw_input("Select header: "))-1]
	
def selectMessage(M):
	M.select()
	data=M.sort('ARRIVAL', 'UTF-8', 'ALL')
	if (data[0]=='OK'):
		j=0
		msg_data=[]
		messages=data[1][0].split(' ')
		lenId=len(str(messages[-1]))
		for i in messages[-15:]:
			typ, msg_data_fetch = M.fetch(i, '(BODY.PEEK[])')
			#print msg_data_fetch
			for response_part in msg_data_fetch:
				if isinstance(response_part, tuple):
					msg = email.message_from_string(response_part[1])
					msg_data.append(msg)
					# Variable length format
					format = "%2s) %"+str(lenId)+"s %-20s %-40s"
					print format %(j,i,email.Header.decode_header(msg['From'])[0][0][:20],email.Header.decode_header(msg['Subject'])[0][0][:40])
					j=j+1
		msg_number = raw_input("Which message? ")
		return msg_data[int(msg_number)] #messages[-10+int(msg_number)-1]
	else:	
		return 0

def selectHeaderAuto(M, msg):
	i=1
	if msg.has_key('List-Id'): 
		return ('List-Id', msg['List-Id'][msg['List-Id'].find('<')+1:-1])
	else:
		for header in msgHeaders:
			if msg.has_key(header):
				print i," ) ", header, msg[header]
			i = i + 1
		header_num=raw_input("Select header: ")
		
		header=msgHeaders[int(header_num)-1]
		textHeader=msg[msgHeaders[int(header_num)-1]]
		pos = textHeader.find('<')
		if (pos>=0):
			textHeader=textHeader[pos+1:textHeader.find('>',pos+1)]
		else:
			pos = textHeader.find('[')
			if (pos>=0):
				textHeader=textHeader[pos+1:textHeader.find(']',pos+1)]
			else:
				textHeader=textHeader
		return (header, textHeader)

def main():
	
	config = ConfigParser.ConfigParser()
	config.read([os.path.expanduser('~/.IMAP.cfg')])

	SERVER = config.get("IMAP1","server")
	USER   = config.get("IMAP1","user")
	PASSWORD=getpass.getpass()

	# Make connections to server
	# Sieve client connection
	c = Client(SERVER)
	c.connect(USER,PASSWORD, starttls=True, authmech="PLAIN")
	# IMAP client connection
	M = imaplib.IMAP4_SSL(SERVER)
	M.login(USER , PASSWORD)

	PASSWORD="@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@" 

	end=""
	while (not end):
		# We are going to filter based on one message
		msg = selectMessage(M)
		(keyword, textHeader) = selectHeaderAuto(M, msg)

		script = c.getscript('sogo')
		p = Parser()
		p.parse(script)

		actions = selectAction(p,M)
		# For a manual selection option?
		#header= selectHeader()
		#keyword = selectKeyword(header)

		header='header'

		print "Filter: (header) ", keyword,", (text) ", textHeader
		filterCond = raw_input("Text for selection (empty for all): ")

		if not filterCond:
			filterCond = textHeader

		conditions=[]
		conditions.append((keyword, ":contains", filterCond))

		print "cond ", conditions, actions, keyword

		fs = FiltersSet("test")
		#fs.addfilter("rule1",
		#                 [("Sender", ":is", "toto@toto.com"), ],
		#                 [("fileinto", "Toto"), ("stop",)])
		#print fs
		print script
		fs.addfilter("",conditions,actions)

		fs.tosieve(open('/tmp/kkSieve','w'))

		p2=Parser()
		p2.parse(open('/tmp/kkSieve','r').read())
		lenP2 = len(p2.result)
		print p2.result[lenP2-1]
		p.result.append(p2.result[lenP2-1])

		#kk=kk+"\n"+open('/tmp/kkSieve','r').read()

		fSieve=open('/tmp/kkSieve','w')
		for r in p.result:
			r.tosieve(0,fSieve)

		fSieve.close()

		# Let's do a backup
		name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
		c.putscript(name+'sogo',script)


		# Now we can put the new sieve filters in place
		fSieve=open('/tmp/kkSieve','r')
		if not c.putscript('sogo',fSieve.read()):
			print "fail!"
		end=raw_input("More rules? (empty to continue) ")

if __name__ == "__main__":
	main()
