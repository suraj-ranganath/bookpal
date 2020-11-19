import oauth2 as oauth
import urllib
import urllib.parse as urlparse
from urllib.parse import urlencode
import webbrowser
from string import Template
import time
import xml.dom.minidom
import sys, getopt
import pandas as pd
import numpy as np
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import os
import config

print("""
 __      __       .__                                  __           __________               __                 .__ ._. 
/  \    /  \ ____ |  |   ____  ____   _____   ____   _/  |_  ____   \______   \ ____   ____ |  | _____________  |  || | 
\   \/\/   // __ \|  | _/ ___\/  _ \ /     \_/ __ \  \   __\/  _ \   |    |  _//  _ \ /  _ \|  |/ /\____ \__  \ |  || | 
 \        /\  ___/|  |_\  \__(  <_> )  Y Y  \  ___/   |  | (  <_> )  |    |   (  <_> |  <_> )    < |  |_> > __ \|  |_\| 
  \__/\  /  \___  >____/\___  >____/|__|_|  /\___  >  |__|  \____/   |______  /\____/ \____/|__|_ \|   __(____  /____/_ 
       \/       \/          \/            \/     \/                         \/                   \/|__|       \/     \/ 
""")
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client1 = gspread.authorize(credentials)

spreadsheet1 = client1.open('user')
spreadsheet2 = client1.open('data')


from goodreads import client
gc = client.GoodreadsClient(config.key, config.secret)


url = 'https://www.goodreads.com'
request_token_url = '%s/oauth/request_token' % url
authorize_url = '%s/oauth/authorize' % url
access_token_url = '%s/oauth/access_token' % url

consumer = oauth.Consumer(key=config.key,
                          secret=config.secret)

client = oauth.Client(consumer)

response, content = client.request(request_token_url, 'GET')
if response['status'] != '200':
    raise Exception('Invalid response: %s, content: ' % response['status'] + content)

request_token1 = dict(urlparse.parse_qsl(content))
request_token = {}
for i in request_token1:
    request_token[i.decode('utf8')] = request_token1[i].decode('utf8')


authorize_link = '%s?oauth_token=%s' % (authorize_url,
                                        request_token['oauth_token'])


webbrowser.open(authorize_link, new=0)
accepted = 'n'
while accepted.lower() == 'n':
    accepted = input('Have you authorized Bookpal to access your Goodreads account? (y/n) ')
print()

token = oauth.Token(request_token['oauth_token'],
                    request_token['oauth_token_secret'])

client = oauth.Client(consumer, token)
response, content = client.request(access_token_url, 'POST')
if response['status'] != '200':
    raise Exception('Invalid response: %s' % response['status'])

access_token1 = dict(urlparse.parse_qsl(content))
access_token = {}

for i in access_token1:
    access_token[i.decode('utf8')] = access_token1[i].decode('utf-8')

accessToken = access_token['oauth_token']
accessTokenSecret = access_token['oauth_token_secret']

gc.authenticate(accessToken, accessTokenSecret)

target_list = 'holding'
token = oauth.Token(accessToken, accessTokenSecret)

client = oauth.Client(consumer, token)

def getUserId():
    response, content = client.request('%s/api/auth_user' % url,'GET')
    if response['status'] != '200':
        raise Exception('Cannot fetch resource: %s' % response['status'])
    userxml = xml.dom.minidom.parseString(content)
    global user_id
    user_id = userxml.getElementsByTagName('user')[0].attributes['id'].value
    return str(user_id)

def sheetsDownloadUser():
    for i, worksheet in enumerate(spreadsheet1.worksheets()):
        with open('user.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            content = worksheet.get_all_values()
            for row in content:
                new_row=[]
                for record in row:
                    new_row.append(record)
                try:
                    writer.writerow(new_row)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    print ("Caught unicode error")

def sheetsDownloadData():
    for i, worksheet in enumerate(spreadsheet2.worksheets()):
        with open('data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            content = worksheet.get_all_values()
            for row in content:
                new_row=[]
                for record in row:
                    new_row.append(record)
                try:
                    writer.writerow(new_row)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    print ("Caught unicode error")


def getShelfBooks(page, shelf_name):
    owned_template = Template('${base}/review/list?format=xml&v=2&id=${user_id}&sort=author&order=a&key=${dev_key}&page=${page}&per_page=100&shelf=${shelf_name}')
    body = bytes(urlencode({}),'utf-8')
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    request_url = owned_template.substitute(base=url, user_id=user_id, page=page, dev_key=***REMOVED***, shelf_name=shelf_name)
    response, content = client.request(request_url, 'GET', body, headers)                                      
    if response['status'] != '200':
        raise Exception('Failure status: %s for page ' % response['status'] + page)
    return content


def getBookInfo(book):
    book_id = book.getElementsByTagName('id')[0].firstChild.nodeValue
    book_title = book.getElementsByTagName('title')[0].firstChild.nodeValue
    return book_id, book_title


def addBookToList(book_id, shelf_name):
    body = urllib.urlencode({'name': shelf_name, 'book_id': book_id})
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response, content = client.request('%s/shelf/add_to_shelf.xml' % url,'POST', body, headers)

    if response['status'] != '201':
        raise Exception('Failure status: %s' % response['status'])
    return True

user_id = getUserId()
username = gc.user(int(user_id)).name
print("Hello {}, great to have you here!!".format(username))

sheetsDownloadUser()
sheetsDownloadData()
users12 = pd.read_csv('user.csv')
usersL = [int(i) for i in users12['UserID'].tolist()]

def user():
    if int(user_id) not in usersL:
        email = input("Please enter your email ID: ")
        regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'

        def check(email):  
            if(re.search(regex,email)):  
                return True 
          
            else:  
                return False
        while check(email):
            if check(email):
                print('Thank You')
                break
            else:
                print('Invalid email ID. Please check and enter it again')
                email = input("Please enter your email ID: ")

        D10 = {'UserID' : [], 'Name' : [], 'EmailID' : []}
        D10['UserID'] += [str(user_id)]
        D10['Name'] += [username]
        D10['EmailID'] += [email]
        dfD = pd.DataFrame(D10)
        dfD.to_csv('user.csv', mode='a', header=False, index = False)
        addBooks()
    else:
        ipt = 0
        while ipt == 0:
            ipt = input("Have you added new books to your Goodreads account since you last used our platform? (y/n)")
            if ipt == 'y':
                addBooks()
            elif ipt == 'n':
                pass
            else:
                print("Enter a valid Input")
                ipt = input("Have you added new books to your Goodreads account since you last used our platform? (y/n)")

def addBooks():
    print("""
 _______________________________________
< This might take a couple of minutes.. >
 ---------------------------------------
        \    ,-^-.
         \   !oYo!
          \ /./=\.\______
               ##        )-\/
                ||-----w||
                ||      ||
""")
    current_page = 0
    total_books = 0
    D = {'UserID' : [], 'BookID' : [], 'BookTitle' : []}
    page1 = 0
    reviewL = []
    while True:
        try:
            reviewL += gc.user(int(user_id)).reviews(page=page1)
            page1+=1
            time.sleep(1)
            if page1 == 100:
                break
        except:
            break

    while True:
        current_page = current_page + 1
        content = (getShelfBooks(current_page, target_list))
        xmldoc = xml.dom.minidom.parseString(content) 
    
        page_books = 0
        for book in xmldoc.getElementsByTagName('book'):
            book_id , book_title = getBookInfo(book)
            D['UserID'] += [int(user_id)]
            D['BookID'] += [int(book_id)]
            D['BookTitle'] += [str(book_title)]

            
            page_books += 1
            total_books += 1

        time.sleep(1)
        if (page_books == 0):
            break

    try:
        data = pd.read_csv('data.csv')
        data1 = pd.DataFrame(D)
        Dfinal = pd.concat([data,data1]).drop_duplicates(['UserID','BookID'],keep='first')
        Dfinal.to_csv('data.csv', index = False)
    except:
        print("error")
        Dfinal = pd.DataFrame(D)
        Dfinal.to_csv('data.csv', index = False)


    #Add user ratings
    dfff = pd.read_csv('data.csv')
    ddfff = dfff.to_dict()
    ddfff['UserRating'] = {}
    ddfff['AvgRating'] = {}
    for i,j in zip(range(len(ddfff['UserID'])), range(len(ddfff['BookID']))):
        if int(ddfff['UserID'][i]) == int(user_id):
            for k in reviewL:
                if int(dict(dict(k.book)['id'])['#text']) == int(ddfff['BookID'][j]):
                    if int(dict(dict(k.book)['id'])['#text']) != 0:
                        ddfff['UserRating'].update({j: int(k.rating)})
                        ddfff['AvgRating'].update({j: float(dict(k.book)['average_rating'])})
    df12 = pd.DataFrame(ddfff)
    df12.to_csv('data.csv',index = False)


#Now to compare grouping by
def compare():
    dk = pd.read_csv('data.csv')
    dk1 = dk[['UserID','BookID']]
    dk1 = dk1.groupby('UserID')['BookID'].apply(list)
    dictK = dk1.to_dict()
    MatchUserID = False
    maxCtr = 0
    CmnBookID = []
    for i in dictK:
        if int(i) != int(user_id):
            S1 = set(dictK[int(user_id)])
            LCom = list(S1.intersection(dictK[i]))
            if len(LCom)>maxCtr:
                maxCtr = len(LCom)
                MatchUserID = i
                CmnBookID = LCom
    if maxCtr == 0:
        print("Sorry, we could not find a book pal for you. Your reading taste is very unique! Check back later.")
    else:
        CmnBook = [gc.book(int(i)).title for i in CmnBookID]
        MatchedUsername = gc.user(int(MatchUserID)).name
        print()
        print("Congrats " + username+", you have been matched with " + MatchedUsername + "!")
        print("You and {} have {} books in common. They are:\n{}".format(MatchedUsername, maxCtr, '\n'.join(CmnBook)))
        
        if int(MatchUserID) in usersL:
            print("Email ID: {}".format(users12[users12['UserID'] == MatchUserID]['EmailID'].to_string(index=False).strip()))
                        

def sheetsUploadUser():
    with open('user.csv', 'r') as file_obj:
        content = file_obj.read()
        client1.import_csv(spreadsheet1.id, data=content)

def sheetsUploadData():
    with open('data.csv', 'r') as file_obj:
        content = file_obj.read()
        client1.import_csv(spreadsheet2.id, data=content.encode('utf-8'))

user()
compare()
sheetsUploadUser()
sheetsUploadData()

if os.path.exists("user.csv"):
    os.remove("user.csv")
if os.path.exists("data.csv"):
  os.remove("data.csv")
  
