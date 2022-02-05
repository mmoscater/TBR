import sqlite3

import numpy as np
import pandas as pd
import requests
import datetime


start_time = datetime.datetime.now()
#sqllite database name
db_name = 'tbr.db'

# vars
api_base = 'http://statsapi.mlb.com'
sports = '/api/v1/sports'
players = '/players'
players_stats = '/api/v1/stats'
teams = '/api/v1/teams'
stat_groups = '/api/v1/statGroups'

### DB MGMT functions
def create_conn(db):
    """ creates a db/connection if none exist """
    conn = None
    try: 
        conn = sqlite3.connect(db)
        #print(f"SUCESS - {sqlite3.version}")
    
    except Exception as e:
        print(e)

    finally:
        if conn:
            conn.close()

def get_tables(db):
    """ returns list of tables within db"""
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        result = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    tables = [r[0] for r in result]
    return tables

def drop_data(db,tables):
    """ drops a list of table from db """
    with sqlite3.connect(db) as conn:
        for t in tables:
            conn.execute(f'drop table {t};')

# API Calls with DB xfrm & loads
def get_all_sports(cxn,id=None):
    """ calls mlb stats api / loads to dimension table and returns dictionary
     of sports (baseball leauge levels)"""
    if id:
        link = '/'.join([sports,id])
    else:
        link = sports
    r = requests.get(''.join([api_base,link]))
    r = r.json()
    sports_dict = r['sports']
    df = pd.DataFrame(sports_dict)
    df = df[['id','abbreviation','name','link']]
    df.to_sql('d_leaguelevel',con=cxn,if_exists='replace',index=False)
    return sports_dict

def get_all_players(cxn,sports_link):
    """ calls mlb stats api / loads to dimension table  and returns list of
     all players"""
    r = requests.get(''.join([api_base,sports_link,players]))
    r = r.json()
    player_cols = ['id','fullName','firstName','lastName','primaryNumber',
        'birthDate','height','weight','currentTeam','primaryPosition',
        'mlbDebutDate','batSide','pitchHand']
    player_list = r['people']
    df = pd.DataFrame(player_list)
    for c in player_cols:
        if c not in df.columns:
            df[c] = np.NaN
    
    df = df[player_cols]
    df['league_id'] = sports_link.split('/')[-1]
    df['primaryPosition'] = df['primaryPosition'].apply(
        lambda x: x.get('code') if not pd.isna(x) else x)
    df['currentTeam'] = df['currentTeam'].apply(
        lambda x: x.get('id') if not pd.isna(x) else x)
    df['batSide'] = df['batSide'].apply(
        lambda x: x.get('code') if not pd.isna(x) else x)
    df['pitchHand'] = df['pitchHand'].apply(
        lambda x: x.get('code') if not pd.isna(x) else x)
    df['mlbDebutDate'] = pd.to_datetime(df.mlbDebutDate).dt.date
    df['birthDate'] = pd.to_datetime(df.birthDate).dt.date
    df.to_sql('d_player',cxn,if_exists='append',index=False)
    return df['id']

def get_teams(cxn):
    """ calls mlb stats api / loads to dimension table  and returns list of
     all teams"""
    r = requests.get(''.join([api_base,teams]))
    r = r.json()
    teams_list = r['teams']
    # missing values fix for High School baseball
    df_missing = pd.DataFrame.from_dict(
        dict(id=[1],name=['Unknown HS Team'],leaguelevel_id=[586],teamCode=['UNK']))
    df = pd.DataFrame(teams_list)
    df = df[['id','name','sport','teamCode']]
    df['sport'] = df['sport'].apply(lambda x: x.get('id'))
    df.rename(columns={'sport':'leaguelevel_id'},inplace=True)
    df = pd.concat([df,df_missing])
    df.to_sql('d_teams',con=cxn,if_exists='replace',index=False)

def get_stat_groups():
    """ calls mlb stats api and returns list of all stat groups"""
    r = requests.get(''.join([api_base,stat_groups]))
    r = r.json()
    return [x.get('displayName') for x in r]

def get_player_season_stats(cxn,group,pool='All',season=2021):
    """ calls mlb stats api / loads to fact table for determined group
     default year is 2020, player pool defaulted to all"""
    leagues = [103,104]
    for l in leagues:
        payload = dict(
            stats='season',
            playerPool=pool,
            group=group,
            season=season,
            leagueId=l)
        r = requests.get(''.join([api_base,players_stats]),params=payload)
        r = r.json()
        df = pd.DataFrame(r['stats'][0].get('splits'))
        df['player_id'] = df['player'].apply(lambda x: x.get('id'))
        df['leaguelevel_id'] = df['sport'].apply(lambda x: x.get('id'))
        df['team_id'] = df['team'].apply(lambda x: x.get('id'))
        df = pd.concat([df,df['stat'].apply(pd.Series)],axis=1)
        df.drop(
            columns=['stat','player','sport','league','team','position','numTeams']
            ,inplace=True)
        df.to_sql(f'f_{group}',cxn,if_exists='append')


def load_stats_data(numYears=4):
    ''' builds database with x years of data from get functions'''

    date = datetime.date.today()
    # checks for regular season end to get full season
    if date.month <= 10:
        year = date.year - 1
    else:
        year = date.year

    # drop tables/create db if not exists
    drop_data(db_name,get_tables(db_name))
    create_conn(db_name)
    cxn = sqlite3.connect(db_name)

    players_list = []
    get_teams(cxn)
    for i in get_all_sports(cxn):
        plyr = get_all_players(cxn,i['link'])
        players_list = players_list + list(plyr)

    stats_groups = get_stat_groups()

    for y in range(year-numYears,year+1,1):
        for sg in stats_groups:
            if sg in ('hitting','pitching'):
                get_player_season_stats(cxn,sg,season=y)


# main
# will load 4 seasons of data
if __name__ == "__main__":
    load_stats_data(4)
    print(f'Load Complete - ExecTime: {datetime.datetime.now()-start_time}')
