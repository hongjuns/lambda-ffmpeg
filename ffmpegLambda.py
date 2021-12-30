import json
import os
import subprocess
import shlex
import boto3
from os.path import getsize
import urllib3
import json
import base64
import io
import datetime
import time

S3_DESTINATION_BUCKET = process.env.BUCKET
OPENAPIURL = "http://aiopen.etri.re.kr:8000/WiseASR/Pronunciation"
ACCESSKEY = process.env.ACCESSKEY
LANGUAGECODE = "english"

def lambda_handler(event, context):

    #querystring Value
    #script = "welcome to the new york city bus tour center"
    script = event["params"]["querystring"]["sciprt"]
    #S3 boot 생성 
    s3_client = boto3.client('s3')

    audioBody = event["body-json"]
    attachment = base64.b64decode(audioBody.encode())
    buff = io.BytesIO(attachment) 
     
    #템프파일생성
    f = open("/tmp/recorder.mp3", "wb")
    f.write(buff.read())
    f.close()

    #파일크기 확인
    fileSzie=getsize("/tmp/recorder.mp3")
    checkSize=round(fileSzie / 1024, 3) 

    if checkSize > 10000 :
      json_object = {
        "responseCode" : "400",
        "responseData" : "파일용량을 초과하였습니다.",
        "checkSize" : checkSize
       }
    else:  
        #현재날짜 
        date = datetime.datetime.now()
        print (("Present date and time:" + date.strftime('%Y-%m-%d:%H.%m.%s')))

        #테스트를위한 mp3파일 s3업로드 (확인용도)
        s3_client.upload_file("/tmp/recorder.mp3", S3_DESTINATION_BUCKET, Key=date.strftime('%Y-%m-%d:%H.%m.%s')+".mp3")
        
        #파일변환 
        ffmpeg_cmd = "/opt/bin/ffmpeg -i /tmp/recorder.mp3 -acodec pcm_s16le -f s16le -ac 1 -ar 16000 " + '/tmp/recorder-data.pcm -y'
        os.system(ffmpeg_cmd)

        file = open("/tmp/recorder-data.pcm", "rb")
        audioContents = base64.b64encode(file.read()).decode("utf8")
        file.close()
        
        #테스트를위한 pcm파일 s3업로드 (확인용도)
        s3_client.upload_file("/tmp/recorder-data.pcm", S3_DESTINATION_BUCKET, Key=date.strftime('%Y-%m-%d:%H.%m.%s')+".pcm")
        
        requestJson = {
            "access_key": ACCESSKEY,
            "argument": {
                "language_code": LANGUAGECODE,
                "script": script, #필수가 아니기에 지워줘도 사용 가능하다.
                "audio": audioContents
            }
        }
        
        http = urllib3.PoolManager()
        response = http.request(
            "POST",
            OPENAPIURL,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            body=json.dumps(requestJson)
        )
        
        print("[responseCode] " + str(response.status))
        print("[responBody]")
        print(str(response.data,"utf-8"))

        json_object = {
            "responseCode" : str(response.status),
            "responseData" : str(response.data,"utf-8")
        }
        
    return {
        'statusCode': 200,
        'body': json.dumps(json_object)
    }
