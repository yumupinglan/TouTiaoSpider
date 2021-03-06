# -*- coding: utf-8 -*-

import re
from urllib import request
from urllib import parse
import json
import time
import pymongo  
import requests
from bs4 import BeautifulSoup
from requests import RequestException
import datetime
import logging

# for the log module
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] -%(levelname)-8s %(message)s',
                    filename='Toutiao.log',
                    datefmt='%m-%d %H:%M',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('[%(asctime)s]%(name)-10s:-%(levelname)-8s %(message)s',datefmt='%m-%d %H:%M')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)
logger_Article = logging.getLogger('Article')
logger_Comment  = logging.getLogger('Comment')
logger_Reply  = logging.getLogger('Reply')
logger_User  = logging.getLogger('User')
logger_Article_list  = logging.getLogger('Article List')

def save_to_mongo(data, coll, **mongo_conn_kw):  
    # Get a reference to a particular database  
    # collection = db[mongo_db_coll]
    # collection.ensure_index('id', unique=True)
    # Reference a particular collection in the database  
    # coll = db[mongo_db_coll]  
    try:  
    # Perform a bulk insert and return IDs  
        return coll.insert(data)  
    except Exception as e:
        # print (e)
        pass
  
def _get_query_string(data):
    return parse.urlencode(data)

def save_user(id):
    query_data = {
            'user_id': id,
        }
    url ='https://is.snssdk.com/user/profile/homepage/v3/' + '?' + _get_query_string(query_data)
    try:
        with request.urlopen(url) as f:
            data_read = f.read()
            data_json = json.loads(data_read.decode('utf-8'))
            data = data_json['data']
            user_data = {
                'name':data['name'],
                'id':data['user_id'],
                'followers_count':data['followers_count'],
                'followings_count':data['followings_count'],
                'verified_content':data['verified_content'],
                'name':data['name'],
            }
            save_to_mongo(user_data, Users)
    except Exception as e:
        logger_User.error("the save_user exception is %s"%(e))
        return
        
def time_parser(timestamp):
    #转换成localtime
    time_local = time.localtime(timestamp)
    #转换成新的时间格式(2016-05-05 20:28:54)
    return time.strftime("%Y-%m-%d %H:%M:%S",time_local)

def save_reply(count, id):
    offset = 0
    count = int(count)
    logger_Reply.info("the replies count is %s"%(count))
    while(1):
        query_data = {
            'comment_id': id,
            'offset': offset,
            'count': 20  # 每次返回 20 篇文章
        }
        url ='http://www.toutiao.com/api/comment/get_reply/' + '?' + _get_query_string(query_data)
        try:
            with request.urlopen(url) as f:
                data_read = f.read()
                data_json = json.loads(data_read.decode('utf-8'))
                data = data_json['data']['data']
                for num in range(0, ((count)%20)):
                    data_item = data[num]
                    if 'text' in data_item:
                        reply_data = {
                            'reply_id':id,
                            'text':data_item['text'],
                            'digg_count':data_item['digg_count'],
                            'create_time':time_parser(int(data_item['create_time'])),
                            'user_id':data_item['user']['user_id'],
                            'name':data_item['user']['name'],
                            'id':data_item['id']
                        }
                        save_user(str(item['comment']['user_id']))
                        save_to_mongo(reply_data, Replies)
        except Exception as e:
            logger_Reply.error('the save_reply exception is %s'%(e))
        offset+=20     
        if (offset-20>count):
            logger_Reply.info('reply is done--------------->')
            return   

def Checktime(starttime,endtime,weibotime):
    Flag=False
    starttime=time.strptime(starttime,'%Y-%m-%d %H:%M:%S')
    endtime=time.strptime(endtime,'%Y-%m-%d %H:%M:%S')
    weibotime=time.strptime(str(weibotime),'%Y-%m-%d %H:%M:%S')
    if int(time.mktime(starttime))<= int(time.mktime(weibotime)) and int(time.mktime(endtime))>=int(time.mktime(weibotime)):
        Flag=True
    else:
        Flag=False
    return Flag

def get_page_detail(url):
    try:
        response = requests.get(url)
        response.encoding='utf-8'
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        logger_Article.error("请求详情页出错 url = %s" % (url))
        return None

def parse_page_detail(html):
    soup = BeautifulSoup(html, 'lxml')
    pattern = "var BASE_DATA"
    script = soup.find_all('script')
    try:
        for n in script:
            n = n.get_text()
            if 'BASE_DATA' in n :
                # 使用json将其转换为dict
                n = n.split('articleInfo: {')
                n = n[1].split('groupId:')
                info = n[0]
                if info:
                    return info
    except:
        return "" 

err_com = ['1572854655127566']
if __name__ == '__main__': 
    error_list = []
    base_url ="http://www.toutiao.com" 
    offset = 0
    i = 0
    # Connect to the MongoDB server running on  
    # localhost:27017 by default  
    client = pymongo.MongoClient(connect=False) 
    # Get a reference to a particular database  
    db = client['Toutiao'] 
    # db = client['Repeat_test'] 
    Articles = db['Articles']
    Comments = db['Comments']
    Users = db['Users']
    Replies = db['Replies']
    Articles.ensure_index('id', unique=True)
    Comments.ensure_index('id', unique=True)
    Users.ensure_index('id', unique=True)
    Replies.ensure_index('id', unique=True)
    # keywords = ['中印','洞朗','中印对峙', '中印边境']
    keywords = ['中印对峙', '中印边境']
    while(i < len(keywords)):
        while(1):
            # keywords = ['中印','洞朗','中印对峙', '中印边境']
            keywords = ['中印对峙', '中印边境']
            query_data = {
                'offset': offset,
                'format': 'json',
                'keyword': keywords[i],
                'autoload': 'true',
                'count': 20,  # 每次返回 20 篇文章
                'cur_tab':1
            }
            url ='http://www.toutiao.com/search_content/' + '?' + _get_query_string(query_data)
            try:
                with request.urlopen(url) as f:
                    data_read = f.read()
                    data_json = json.loads(data_read.decode('utf-8'))
                    data = data_json['data']
                    return_count = int(data_json['return_count'])
                    logger_Article_list.info("this search url is handling %s"%(url))
                    if(return_count ==0):
                        logger_Article_list.info("this keyword is done++++++++++++++++！！！！！！！！！！！！！！！！！！！！")                    
                        break;    
                    logger_Article.info('return_count:%s'%(return_count))
                    for num in range(0,return_count): 
                        logger_Article.info('Article: %s'% (str(num)))
                        data_item = data[num]
                        flag = True
                        # print (data_item)
                        if 'datetime' in data_item and 'id' in data_item:
                            logger_Article.info("the date time is %s  and the id is %s"%(data_item['datetime'],data_item['id']))
                            have_comments = Comments.find({'article_id':data_item['id']}).count()
                            for id in  Articles.find({"id":data_item['id']}): 
                                logger_Article.warning("Already got it %s %s"%( id['id'],id['title']))
                                flag = False
                                logger_Article.info("we find commens is 【%s】 but the collection has 【%s】"%(data_item['comments_count'],have_comments))
                            # if data_item['comments_count'] > have_comments:
                            #     # 没爬到的大于总评论的千分之一？
                            #     if (data_item['comments_count'] - have_comments)/data_item['comments_count'] > 0.1:
                            #         # 没爬到的帖数大于3？
                            #         if data_item['comments_count'] - have_comments > 3:
                            #             if have_comments < 1000 :
                            #             # 重新爬
                            #                 logger_Article.warning("But we still gonna to crawl it for unfinished comments :-)")
                            #                 flag = True
                            if Checktime('2017-06-18 0:0:0','2017-08-29 0:0:0',data_item['datetime']+':00') and flag:
                                    # id_finish_article.append(data_item['id'])
                                    media_name = "参考消息"
                                    media_url = ""
                                    if 'media_name' in data_item:
                                        media_name = data_item['media_name'] #发布者名字
                                        media_url = data_item['media_url'] #发布者名字
                                    title = data_item['title']
                                    id = data_item['id']
                                    logger_Article.info("Now clawling article is %s"%(title))
                                    article_url = data_item['article_url']#文章url
                                    datetime = data_item['datetime']
                                    comments_count = int(data_item['comments_count'])
                                    download_url = 'http://www.toutiao.com/a'+str(id) +'/'
                                    html = get_page_detail(download_url)
                                    content = parse_page_detail(html)
                                    new_data = {
                                        'media_name':media_name,
                                        'title':title,
                                        'id':id,
                                        'article_url':article_url,
                                        'content':content,
                                        'datetime':datetime,
                                        'comments_count':comments_count,
                                        'digg_count':data_item['digg_count'],
                                        'bury_count':data_item['bury_count'],
                                        'favorite_count':data_item['favorite_count'],
                                        'item_source_url':base_url+data_item['item_source_url']
                                    }
                                    save_to_mongo(new_data, Articles)
                                    if 'media_creator_id' in data_item:
                                        save_user(str(data_item['media_creator_id']))
                                    offset_comment = have_comments-20 if have_comments>20 else 0
                                    count = 20
                                    while(offset_comment < comments_count):#每次+20
                                        query_data_comment = {
                                            'group_id': id,
                                            'offset': offset_comment
                                        }
                                        comment_url ='https://is.snssdk.com/article/v2/tab_comments/'+'?'+_get_query_string(query_data_comment)
                                        with request.urlopen(comment_url) as f_comment:
                                            data_read_comment = f_comment.read()
                                            data_json_comment = json.loads(data_read_comment.decode('utf-8'))
                                            data_comment = data_json_comment['data']
                                            if data_json_comment['total_number']==0:
                                                logger_Comment.info('the comment is done ')
                                                break
                                            for item in data_comment:
                                                comment_id = item['comment']['id']
                                                logger_Comment.info("the comment ID is  %s"%(comment_id))
                                                comment_data = {
                                                    'article_id':id,
                                                    'id':comment_id,
                                                    'text':item['comment']['text'],
                                                    'create_time':time_parser(int(item['comment']['create_time'])),
                                                    'score':item['comment']['score'],
                                                    'user_id':item['comment']['user_id'],
                                                    'user_name':item['comment']['user_name'],
                                                    'digg_count':item['comment']['digg_count'],
                                                    'bury_count':item['comment']['bury_count'],
                                                    'reply_count':item['comment']['reply_count']
                                                }
                                                save_user(str(item['comment']['user_id']))
                                                save_to_mongo(comment_data, Comments)
                                                if (int(item['comment']['reply_count'])!=0):
                                                    save_reply(str(item['comment']['reply_count']),str(comment_id))
                                        offset_comment += count;
                offset+=20
            except Exception as e:
                logger_Article_list.error( "the main while has an exception is %s"%e)
        i+=1
        offset = 0
        logger_Article_list.info('one keyword is done :)')
    logger_Article_list.info('everything is done :)')
    client.close()