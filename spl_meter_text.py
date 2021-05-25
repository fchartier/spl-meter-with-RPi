#!/usr/bin/env python3
import os, errno
import pyaudio
import spl_lib as spl
from scipy.signal import lfilter
import numpy
import csv
import datetime
import argparse

## For web browser handling
#from selenium import webdriver


''' The following is similar to a basic CD quality
   When CHUNK size is 4096 it routinely throws an IOError.
   When it is set to 8192 it doesn't.
   IOError happens due to the small CHUNK size

   What is CHUNK? Let's say CHUNK = 4096
   math.pow(2, 12) => RATE / CHUNK = 100ms = 0.1 sec
'''
CHUNKS = [4096, 9600]       # Use what you need
CHUNK = CHUNKS[1]
FORMAT = pyaudio.paInt16    # 16 bit
CHANNEL = 1    # 1 means mono. If stereo, put 2

'''
Different mics have different rates.
For example, Logitech HD 720p has rate 48000Hz
'''
RATES = [44300, 48000]
RATE = RATES[1]

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

def get_path(base, tail, head=''):
    return os.path.join(base, tail) if head == '' else get_path(head, get_path(base, tail)[1:])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = get_path(BASE_DIR, 'html/main.html', 'file:///')
SINGLE_DECIBEL_FILE_PATH = get_path(BASE_DIR, 'decibel_data/single_decibel.txt')
MAX_DECIBEL_FILE_PATH = get_path(BASE_DIR, 'decibel_data/max_decibel.txt')

START_DATE = datetime.datetime.now()
CSV_FILE_PATH = get_path(BASE_DIR, 'decibel_data/spl-meter-output-%s.csv' % START_DATE.strftime("%y%m%d_%H%M%S"))

parser = argparse.ArgumentParser("SPL Meter")
parser.add_argument('-csv', action="store_true", help="Generate CSV file")
args = parser.parse_args()

GENERATE_CSV = args.csv



'''
Listen to mic
'''
pa = pyaudio.PyAudio()

stream = pa.open(format = FORMAT,
                channels = CHANNEL,
                rate = RATE,
                input = True,
                frames_per_buffer = CHUNK)


def is_meaningful(old, new):
    return abs(old - new) > 3

def is_time(old, new):
    return (new - old).total_seconds() >= 30

def update_text(path, content):
    try:
        f = open(path, 'w')
    except IOError as e:
        print(e)
    else:
        f.write(content)
        f.close()

def click(id):
    driver.find_element_by_id(id).click()

def open_html(path):
    driver.get(path)

def update_max_if_new_is_larger_than_max(new, max):
    print("update_max_if_new_is_larger_than_max called")
    if new > max:
        print("max observed")
        update_text(MAX_DECIBEL_FILE_PATH, 'MAX: {:.2f} dBA'.format(new))
        click('update_max_decibel')
        return new
    else:
        return max


def listen(old=0, error_count=0, min_decibel=100, max_decibel=0):
    print("Listening")
    if GENERATE_CSV:
        f_out = open(CSV_FILE_PATH, "w")
        writer = csv.writer(f_out)
        writer.writerow(["timestamp", "value_db"])
    old_time = START_DATE

    while True:
        try:
            ## read() returns string. You need to decode it into an array later.
            block = stream.read(CHUNK)
        except IOError as e:
            error_count += 1
            print(" (%d) Error recording: %s" % (error_count, e))
        else:
            ## Int16 is a numpy data type which is Integer (-32768 to 32767)
            ## If you put Int8 or Int32, the result numbers will be ridiculous
            decoded_block = numpy.fromstring(block, 'Int16')
            ## This is where you apply A-weighted filter
            y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
            new_decibel = 20*numpy.log10(spl.rms_flat(y))
            new_time = datetime.datetime.now()
            if GENERATE_CSV and (is_meaningful(old, new_decibel) or is_time(old_time, new_time)):
                writer.writerow([
                    # datetime.datetime.now().replace(microsecond=0).isoformat(), 
                    datetime.datetime.now().isoformat(), 
                    "%0.2f" % new_decibel
                    ])
                f_out.flush()
                old_time = new_time
            if is_meaningful(old, new_decibel):
                old = new_decibel
                print('A-weighted: {:+.2f} dB'.format(new_decibel))
                #update_text(SINGLE_DECIBEL_FILE_PATH, '{:.2f} dBA'.format(new_decibel))
                #max_decibel = update_max_if_new_is_larger_than_max(new_decibel, max_decibel)
                #click('update_decibel')

    if GENERATE_CSV:
        f_out.close()
    stream.stop_stream()
    stream.close()
    pa.terminate()



if __name__ == '__main__':
    #driver = webdriver.Firefox()
    #open_html(HTML_PATH)
    listen()
    #driver.close()
