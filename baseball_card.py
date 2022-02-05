
import sqlite3
from flask import Flask, render_template
import os
from datetime import date

PHOTO = os.path.join('static','player_photo')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = PHOTO
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def get_db_cxn():
    cxn = sqlite3.connect('tbr.db')
    cxn.row_factory = sqlite3.Row
    return cxn

@app.route('/')
def index():
    # cxn = get_db_cxn()
    # tables = cxn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    # fmt_tables = [t for t in tables if t[0 ]=='d']
    return render_template('main.html')

@app.route('/<level>/<int:team>/players')
def players(level='all',team=0):
    cxn = get_db_cxn()
    players = cxn.execute(
        f"""select distinct p.fullName,p.id,l.abbreviation,p.lastName,t.id,t.name 
        from d_player p
        inner join d_leaguelevel l on l.id = p.league_id
        inner join d_teams t on t.id = p.currentTeam
        WHERE (l.abbreviation = '{level}' or 'all' = '{level}') and
            (t.id = {team} or {team} = 0)
        order by p.lastName asc ,firstName asc;""").fetchall()
    cxn.close()
    return render_template('players.html',players=players)

@app.route('/<level>/teams')
def teams(level):
    cxn = get_db_cxn()
    players = cxn.execute(
        f"""select distinct t.id as id,t.name as team, l.abbreviation,l.name
        from d_teams t
        inner join d_leaguelevel l on l.id = t.leaguelevel_id
        where l.abbreviation = '{level}' or 'all' = '{level}';""").fetchall()
    cxn.close()
    return render_template('teams.html',players=players)

@app.route('/level')
def level():
    cxn = get_db_cxn()
    players = cxn.execute(
        """select distinct *
        from d_leaguelevel;""").fetchall()
    cxn.close()
    return render_template('level.html',players=players)

@app.route("/players/<int:id>")
def player(id):
    pitcher_img = os.path.join(app.config['UPLOAD_FOLDER'],'pitcher.png')
    batter_img = os.path.join(app.config['UPLOAD_FOLDER'],'batter.png')
    cxn = get_db_cxn()
    player = cxn.execute(f"""
    select p.fullName,
            t.name,
            p.primaryNumber,
            l.abbreviation,
            l.name as 'league',
            p.primaryPosition,
            p.height,
            p.weight,
            p.batSide,
            p.pitchHand,
            STRFTIME('%m/%d/%Y',p.mlbDebutDate) as mlbDebutDate,
            STRFTIME('%m/%d/%Y',p.birthDate) as birthDate,
            CASE p.primaryPosition
                WHEN 1
                THEN 'P'
                WHEN 2
                THEN 'C'
                WHEN 3
                THEN '1B'
                WHEN 4
                THEN '2B'
                WHEN 5
                THEN '3B'
                WHEN 6
                THEN 'SS'
                WHEN 7
                THEN 'LF'
                WHEN 8
                THEN 'CF'
                WHEN 9
                THEN 'RF'
                ELSE 'UTIL'
            END position
    from d_player as p
    join d_leaguelevel l on l.id = p.league_id
    join d_teams t on t.id = p.currentTeam 
    where p.id ={id};""").fetchone()
    # cxn.close()
    hitting = cxn.execute(f"""
    select h.*,UPPER(t.teamCode) teamCode from f_hitting h
    join d_teams t on t.id = h.team_id
    where player_id ={id}
    order by season desc;""").fetchall()
    # cxn.close()
    pitching = cxn.execute(f"""
    select p.*,UPPER(t.teamCode) teamCode from f_pitching p
    join d_teams t on t.id = p.team_id
    where player_id ={id}
    order by season desc;""").fetchall()
    cxn.close()
    return render_template('player.html',player=player,pitching=pitching,hitting=hitting)



if __name__ == '__main__':
    app.run(host="0.0.0.0")