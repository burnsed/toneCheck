import datetime
import os
import requests
import shutil
import uuid
import xlrd
import xlwt

from flask import (Flask,
                   request,
                   render_template,
                   jsonify,
                   send_from_directory)

app = Flask(__name__)

TMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp")
FEED_ID = "7238"
AUDIO_FEED_BASE = "https://m.broadcastify.com/archives/ajax.phpdate=03/22/2021&_=1616470965284"
OUTPUT_FILE = os.path.join(TMP_DIR, "output.xls")


def find_clips(start_time, end_time):
    """
    @param start_time: UTC start time of clip segment
    @param end_time: UTC end time of clip segment
    @return: list of broadcastify.com feed ids
    """
    dates = set([start_time.date(), end_time.date()])
    clip_ids = []
    for date in dates:
        params = {
            "feedId": FEED_ID,
            "date": date.strftime("%m/%d/%Y")
        }
        r = requests.get(AUDIO_FEED_BASE, params=params)
        response = r.json()
        
        # Walk through the responses for the day and find the matching audio clips for that day
        for file_id, start, end in response["data"]:
            # FIXME: implement
            print("File: %s, start: %s, end: %s"%(file_id, start, end))


def find_tone_time(clip):
    """
    @param clip: broadcastify.com feed id 
    @return: tone_start_offset, tone_msg_end_offset
      tone_start_offset - the offset in seconds from the beginning of the clip when the tone outs are first heard
      tone_msg_end_offset - the offset in seconds from the beginning of the clip when the tone out message ends
    """
    return


def process_tone(dispatch_time, responding_time):
    # convert timestamps from Excel to utc
    dt = datetime.datetime.utcfromtimestamp((dispatch_time - 25569)* 86400)
    rt = datetime.datetime.utcfromtimestamp((responding_time - 25569)* 86400)

    # Pull the audio a few seconds before the dispatch time
    start_time = dt - datetime.timedelta(seconds=3)
    end_time = rt + datetime.timedelta(minutes=2)

    clips = find_clips(start_time, end_time)
    radio_time = None
    for clip_time, clip in clips:
        offset = find_tone_time(clip)
        if offset:
            radio_time = clip_time + offset
            break
    
    if not radio_time:
        raise Exception("Tones not detected in clip: %s"%(clip))
    
    # Find the acknowldge time
    # FIXME: implement voice to text
    acknowledge_time = responding_time

    return tone_start, tone_end, response_said, response_acknowleged


def process_worksheet(worksheet):
    #
    # Line 0: title
    # Line 1: blank
    # Line 2: header
    # Line 3-EOF: dispatch rows
    #
    # Columns:
    #    0       1           2              3           4
    #   Unit, Call No, Dispatch Time, En Route Time, Elapsed
    header = worksheet.row_values(2)
    header.insert(7, "ELAPSED MAX")
    header.insert(7, "ELAPSED MIN")
    header.insert(6, "COPY RESPONDING")
    header.insert(6, "SAID RESPONDING")
    header.insert(5, "TONE END")
    header.insert(5, "TONE START")

    new_sheet = [[c for c in worksheet.row_values(0) if c is not None]]
    new_sheet.append([c for c in worksheet.row_values(1) if c is not None])
    new_sheet.append(header)
    for row_idx in range(3, worksheet.nrows):
        row = worksheet.row_values(row_idx)
        # skip the 0s
        if row[4] <= 0:
            continue
        # FIXME: finish implementing
        # tone_start, tone_end, responding_said, responding_copy = process_tone(row[2], row[3])
        # elapsed_max = responding_copy - tone_start
        # elapsed_min = responding_said - tone_end
        # row.insert(5, elapsed_max)
        # row.insert(5, elapsed_min)
        # row.insert(4, responding_copy)
        # row.insert(4, responding_said)
        # row.insert(3, tone_end)
        # row.insert(3, tone_start)

        # FIXME: remove
        # FIXME: insert positions are wrong. Also have this write the entire sheet
        row.insert(7, "pending")
        row.insert(7, "pending")
        row.insert(6, "pending")
        row.insert(6, "pending")
        row.insert(5, "pending")
        row.insert(5, "pending")

        new_sheet.append(row)
    
    return new_sheet


@app.route('/parse-file', methods=['POST'])
def parse_file():
    file_obj = request.files['0']
    report_filepath = os.path.join(TMP_DIR, str(uuid.uuid4())+".xlsx")  
    file_obj.save(report_filepath)

    # Open & parse the xlsx
    # try:
    if True:
        workbook = xlrd.open_workbook(report_filepath)
        worksheet = workbook.sheet_by_index(0)

        # Process the data in the worksheet
        new_sheet = process_worksheet(worksheet)
        
        # write the output file
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('tones')

        y = 0
        for row in new_sheet:
            for x in range(0, len(row)):
                if row[x] is not None:
                    sheet.write(y, x, row[x])
            y += 1
        workbook.save(OUTPUT_FILE)
        print("Wrote to %s"%OUTPUT_FILE)

    else:
    # except Exception as e:
        response = {
            "success": False,
            "error_message": str(e)
        }
        return jsonify(response), 200

    response = {
        "success": True,
    }
    return jsonify(response), 200


@app.route('/', methods=['GET'])
def main():
    if not os.path.isfile(OUTPUT_FILE):
        return render_template("index.html", table_content="")

    workbook = xlrd.open_workbook(OUTPUT_FILE)
    worksheet = workbook.sheet_by_index(0)
    table = ""
    
    # table header
    header = [c for c in worksheet.row_values(2) if c is not None]
    time_columns = []
    for x in range(0, len(header)):
        if "TIME" in header[x]:
            time_columns.append(x)

    table += "<thead>"
    table += "<tr>"
    table += "\n".join(['''<th scope="col" class="text-nowrap">%s</th>'''%(col) for col in header])
    table += "\n</tr>\n</thead>"

    # table body
    # FIXME: add sorting on dispatch time
    table += "<tbody>\n"
    for row_idx in range(3, worksheet.nrows):
        row = [c for c in worksheet.row_values(row_idx) if c is not None]
        new_row = []
        for x in range(0, len(row)):
            if x in time_columns:
                dt = xlrd.xldate_as_tuple(row[x], 0)
                # dt(year, month, day, hour, minute, second)
                new_row.append("%d/%d/%d %2d:%2d:%2d"%(dt[1], dt[2], dt[0], dt[3], dt[4], dt[5]))
            else:
                new_row.append(row[x])
        table += "<tr>\n"
        table += "\n".join(['''<td class="text-nowrap">%s</td>'''%(col) for col in new_row])
        table += "\n</tr>\n"
    table += "</tbody>"
    return render_template("index.html", table_content=table)

@app.route('/toneCheck.xls', methods=['GET'])
def tone_check_download():
    return send_from_directory(directory=TMP_DIR, filename="output.xls")

@app.errorhandler(404)
def not_found(e):
    message = "404 We couldn't find the page"
    return render_template("index.html", error_message=message)


if __name__ == "__main__":
    IS_PROD = os.environ.get("IS_PROD", False)
    if not os.path.isdir(TMP_DIR):
        os.mkdir(TMP_DIR)

    app.run(debug=not IS_PROD, host="0.0.0.0", threaded=True)
