import time

from flask import *
from deepgram import Deepgram
from dotenv import load_dotenv
import os
import asyncio
from aiohttp import web
from aiohttp_wsgi import WSGIHandler
from typing import Dict, Callable
import string
import pyrebase

from datetime import datetime,date

# Libraries used for getting data from Firebase and display on webpage
import csv

# Plotting using libraries
from bokeh.plotting import figure, output_file, show
import pandas as pd
import numpy as np
from bokeh.layouts import layout
from bokeh.io import curdoc
from bokeh.models import HoverTool

load_dotenv()

config = {
    "apiKey": "AIzaSyD7IYK6nNprDHxFEWWsGEfR_u13ECdlJ34",
    "authDomain": "tempbackend-7c9b3.firebaseapp.com",
    "databaseURL": "https://tempbackend-7c9b3-default-rtdb.firebaseio.com",
    "projectId": "tempbackend-7c9b3",
    "storageBucket": "tempbackend-7c9b3.appspot.com",
    "messagingSenderId": "17153523147",
    "appId": "1:17153523147:web:d597c786940c4392c08a4e",
    "measurementId": "G-W4KBLDEWDL"
}

firebase = pyrebase.initialize_app(config)

db = firebase.database()

usersI = db.child("kidcommImages").get()
dictI = usersI.val()
img = list(dictI.values())

usersT = db.child("kicommText").get()
dictT = usersT.val()
lines = list(dictT.values())

app = Flask(__name__)

dg_client = Deepgram('ad174cf3a007ca9853c2bbe7a72ab7978597a466')

count = 1

start = 0
end = 0
time_taken = 0

# Key : Value
# Line_no : [accuracy, time_taken, words_per_minute, wrong_words]
performance_dict = {}

final_dict = {"Accuracy":0, "Time_taken":0, "Speed":0}
total_accuracy = 0
avg_accuracy = 0
total_time_taken = 0
avg_time_per_line = 0
total_speed = 0
avg_words_per_sec = 0

plot_flag = 0

story_play = 1

accuracy = 0

# =================Plotting graphs =======================
def plot_attemptsPerDay(df):
    dates = df['Date of Attempt']
    min_date = dates[0]
    max_date = dates[0]

    dic = {}

    for i in range(0, len(dates)):
        min_date = min(min_date, dates[i])
        max_date = max(max_date, dates[i])

        if (dates[i] in dic):
            dic[dates[i]] = dic[dates[i]] + 1
        else:
            dic[dates[i]] = 1

    print(min_date, max_date, '$')
    date_generated = pd.date_range(min_date, max_date)
    # print('date generated : ',date_generated)
    date_generated_2 = date_generated.strftime("%Y-%m-%d")
    print(date_generated[0] == min_date)
    y = []

    for i in range(len(date_generated_2)):
        if (date_generated_2[i] in dic):
            y.append(dic[date_generated_2[i]])
        else:
            y.append(0)

    # Current streak
    curr = 0
    for i in range(len(y) - 1, 0, -1):
        if (y[i] == 0):
            break
        curr += 1
    print("CURRENT STREAK : ", curr, y)
    output_file("datetime_3.html")
    curdoc().theme = 'dark_minimal'
    # Attempts every day
    x = date_generated
    pl = figure(title="Attempts History", width=750, height=350, x_axis_type="datetime",
                x_range=(date_generated[0], date_generated[len(y) - 1]), y_range=(0, 2), x_axis_label='Date',
                y_axis_label='Attempts')
    pl.title.text_font_size = '15pt'
    pl.vbar(x, top=y, width=36000000)

    # Accuracy trend
    pl_2 = figure(title="Accuracy Trend", width=750, height=350, x_range=(1, len(df) + 1), y_range=(0, 100),
                  x_axis_label='Number of Attempts', y_axis_label='Averaged Accuracy')
    pl_2.title.text_font_size = '15pt'

    attempts = np.linspace(1, len(df), num=len(df))
    pl_2.line(attempts, df['Averaged accuracy(Till Now)'], color="yellow", alpha=1, width=2)

    cr = pl_2.circle(attempts, df['Averaged accuracy(Till Now)'], size=20, fill_color="grey",
                     hover_fill_color="firebrick", fill_alpha=0.05, hover_alpha=0.3, line_color=None,
                     hover_line_color="white")

    pl_2.add_tools(HoverTool(tooltips=None, renderers=[cr], mode='hline'))

    # Plotting fluency curve

    pl_3 = figure(title="Fluency Trend", width=1500, height=350, x_range=(1, len(df) + 1), y_range=(0, 5),
                  x_axis_label='Number of Attempts', y_axis_label='Speed (Words/Sec)')
    pl_3.title.text_font_size = '15pt'

    pl_3.line(attempts, df['Speed(words/sec)'], color="red", alpha=1, width=2)

    cr = pl_3.circle(attempts, df['Speed(words/sec)'], size=20, fill_color="grey", hover_fill_color="firebrick",
                     fill_alpha=0.05, hover_alpha=0.3, line_color=None, hover_line_color="white")

    pl_3.add_tools(HoverTool(tooltips=None, renderers=[cr], mode='hline'))

    # Plotting them side by side
    show(layout([[pl, pl_2], [pl_3]]))
    print(dic)


def update_df(df, Player_Name, Time_taken, speed, accuracy, para_ID, date):
    sums = df['Averaged accuracy(Till Now)'][len(df) - 1] * len(df)
    new_avg = (sums + accuracy) / (len(df) + 1)
    new_row = {'Player Name': Player_Name, 'Time taken': Time_taken, 'Speed(words/sec)': speed, 'Accuracy': accuracy,
               'Paragraph ID': para_ID, 'Averaged accuracy(Till Now)': new_avg, 'Date of Attempt': date}
    df = df.append(new_row, ignore_index=True)
    return (df)

# ========================= Taking data from Firebase ==================================
def retrieveFirebaseData():
    user_dict = (db.child("Data").child("Kalam").get()).val()

    date_keys = list(user_dict.keys())

    user_data = []
    # for time stamps in a date
    for date in date_keys:
        time_keys = list(user_dict[date].keys())
        for time in time_keys:
            acc = user_dict[date][time]["Accuracy"]
            speed = user_dict[date][time]["Speed"]
            time_taken = user_dict[date][time]["Time"]
            user_data.append([date, time, acc, speed, time_taken])

    with open('users.csv', 'w', newline='') as file:
        fieldnames = ['Date', 'Time', 'Accuracy', 'Speed', 'Time taken']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        for row in user_data:
            writer.writerow({'Date': row[0], 'Time': row[1], 'Accuracy': row[2], 'Speed': row[3], 'Time taken': row[4]})

# ========================= Working on Speech data =========================================
async def createWordlist(s):
    new_s = s.translate(str.maketrans('', '', string.punctuation))
    word_list = []
    lower_s = new_s.lower()
    for word in lower_s.split(" "):
        word_list.append(word)
    return word_list


async def createTranscript(s, common_words):
    new_s = s.translate(str.maketrans('', '', string.punctuation))
    new_s = new_s.lower()
    word_list = []
    for word in new_s.split(" "):
        if word in common_words:
            word_list.append(word.upper())
        else:
            word_list.append(word)
    sentence = ' '.join(word_list)
    return sentence


async def speechMatch(speechLine, storyLine):
    # Remove all punctuations, convert everything to lowercase
    # Create a dictionary of words (hashmap)
    # If more than half words are matched, then goto next page
    speechList = await createWordlist(speechLine)
    storyList = await createWordlist(storyLine)
    common_words = set(speechList) & set(storyList)
    wrong_words = set(storyList).difference((set(speechList) & set(storyList)))
    common_words_len = len(set(speechList) & set(storyList))
    total_words = len(set(storyList))
    percent_overlap = common_words_len / float(total_words)

    # print(overlap_words, ",", total_words, ",", percent_overlap)
    return percent_overlap, common_words, wrong_words

# ============== Connecting to websocket to display on index4.html ==================
async def process_audio(fast_socket: web.WebSocketResponse):

    async def get_transcript(data: Dict) -> None:
        if 'channel' in data and story_play==1:
            transcript = data['channel']['alternatives'][0]['transcript']

            global total_accuracy, avg_accuracy, total_time_taken, avg_time_per_line, avg_words_per_sec, total_speed
            global plot_flag
            global accuracy

            if transcript:
                global count, start, end, time_taken
                accuracy, common_words, wrong_words = await speechMatch(transcript, lines[count])
                accuracy = round(accuracy, 2)

                # Highlight common words in CAPS, rest in small letters
                new_transcript = await createTranscript(transcript, common_words)

                end = time.time()
                time_taken = round(end - start, 2)
                start = end

                speed = round((time_taken / len(lines[count].split())), 2)

                # if speech is greater than threshold
                if accuracy >= 0.4:
                    if count==1: # First line is getting wrong values for time, so omit it for time being by making them 0
                        accuracy = 0
                        speed = 0
                        time_taken = 0

                    total_accuracy += accuracy
                    total_speed += speed
                    total_time_taken += time_taken

                    performance_dict[count] = [accuracy, time_taken, speed]

                    # When we reached end of story
                    if count == 5 and plot_flag == 0:
                        avg_accuracy = round((total_accuracy / (count-1)), 2)
                        avg_time_per_line = round((total_time_taken / (count-1)), 2)
                        avg_words_per_sec = round((total_speed / (count-1)), 2)

                        print("Linewise data : [Accuracy, Time_taken, Speed(words/min)]")
                        print(performance_dict)
                        print("Story data : [Avg_Accuracy, Avg_Time_taken, Avg_Speed(words/min)]")
                        print(avg_accuracy, avg_time_per_line, avg_words_per_sec)

                        today = date.today()
                        today = today.strftime("%d-%m-%Y")

                        now = datetime.now()
                        current_time = now.strftime("%H:%M:%S")

                        data = {'Accuracy': avg_accuracy, 'Time': avg_time_per_line, 'Speed': avg_words_per_sec}
                        db.child('Data').child("Kalam").child(today).child(current_time).set(data)

                        retrieveFirebaseData()

                        df = pd.read_csv(r'D:\pythonProject\WebProject\SpeechRecognition4\Player.csv', index_col=0)
                        plot_attemptsPerDay(df)

                        plot_flag = 1

                    count += 1
                    print("Line no = " + str(count))

                image = img[count]
                print(image)
                if accuracy >= 0.4 or (accuracy==0 and count==2):
                    print("1")
                    await fast_socket.send_str(new_transcript + ";" + image + ";" + "1" + ";" + str(count))
                else:
                    print("0")
                    await fast_socket.send_str(new_transcript + ";" + image + ";" + "0" + ";" + str(count))

                accuracy = 0

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket


async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]) -> str:
    try:
        socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')


# @app.route('/')
# def index():
#     return render_template('index4.html')

ws = web.WebSocketResponse()

async def socket(request):
    global ws
    await ws.prepare(request)

    deepgram_socket = await process_audio(ws)

    while not ws.closed:
        data = await ws.receive_bytes()
        deepgram_socket.send(data)

async def button_socket(button_request):
    global count, ws, story_play
    button_ws = web.WebSocketResponse()
    await button_ws.prepare(button_request)

    while not button_ws.closed:
        button_data = await button_ws.receive_str()
        print(button_data)
        print(type(button_data))
        if button_data=='Prev_button':
            count -= 1
            image = img[count]
            await ws.send_str("_ _ _ _ _" + ";" + image + ";" + "1" + ";" + str(count))
        elif button_data=='Next_button':
            count += 1
            image = img[count]
            await ws.send_str("_ _ _ _ _" + ";" + image + ";" + "1" + ";" + str(count))
        elif button_data=="Pause":
            image = img[count]
            await ws.send_str("Story Paused" + ";" + image + ";" + "1" + ";" + str(count))
            story_play = 0
        elif button_data=="Play":
            image = img[count]
            await ws.send_str("_ _ _ _ _" + ";" + image + ";" + "1" + ";" + str(count))
            story_play = 1
        print(count)

routes = web.RouteTableDef()
def html_response(document):
    s = open(document, "r")
    return web.Response(text=s.read(), content_type='text/html')

@app.route('/')
def index():
    return render_template('home.html')

@routes.get('/story')
async def main_handler(request):
    return html_response('templates/new_index.html')

@routes.get('/output')
async def output_handler(request):
    return html_response('templates/output.html')

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    aio_app = web.Application()
    wsgi = WSGIHandler(app)
    aio_app.router.add_route('*', '/{path_info: *}', wsgi.handle_request)
    aio_app.router.add_route('GET', '/listen', socket)
    aio_app.router.add_route('GET', '/button', button_socket)
    aio_app.add_routes(routes)
    web.run_app(aio_app, host='0.0.0.0', port=8029)
