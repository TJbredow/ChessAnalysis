import json
from operator import itemgetter
from flask import Flask, render_template, request
from markupsafe import escape
from pprint import pprint
from user_analysis import PlayerNotFound, UserData


app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def main():
    if request.method == 'POST':
        print(request.form)
        username = escape(request.form.get('PlayerName'))
        if username:
            try:
                user_data =  UserData(username)
                analysis_data = user_accordion(user_data, request.form.get('analysisColor'))
            except PlayerNotFound:
                return render_template('index.html', error_template='Player Not Found')
            return render_template('index.html', accordion_data=analysis_data)
        else:
            print('fail')

    return render_template('index.html')

def user_accordion(user_data: UserData, analysis_color: str) -> dict:
    analysisdeep =  sorted(
                            user_data.analysis(analysis_color,
                            datatype='notdf').items(),
                            key = lambda x: x[1]['gamesplayed'], reverse=True)
    analysisfamily = sorted(
                            user_data.analysis(analysis_color,
                            openingdepth='family', datatype='notdf').items(),
                            key = lambda x: x[1]['gamesplayed'], reverse = True)
    accordion_data = {}
    for opening in analysisfamily:
        accordion_data[opening[0]] = opening[1]
        accordion_data[opening[0]]['variations'] = {}
        for variation in analysisdeep:
            if accordion_data[opening[0]]['moves'] in variation[1]['moves']:
                accordion_data[opening[0]]['variations'][variation[0]] = variation[1]
    with open(f'playercache/{user_data.user}.json','w') as jsonfile:
        jsonfile.write(json.dumps(accordion_data, indent=2, sort_keys=False))
    return accordion_data

