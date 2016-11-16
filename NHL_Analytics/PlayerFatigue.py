# Brendan Thorn - November 2016
# A program to test whether the correlation between player size and fatigue, to the
# extent that it show up in periods with high game densities.

# NOTE: If you're having problems running the program, check that the config json file
# matches your system configurations, and that the db is properly named in StatsDB.py

import MySQLdb, re, time, sys, datetime, math, signal
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import StatsDB


class PlayerData():

	def __init__(self,season=20152016,min_games=41):
		self.db = StatsDB.StatsDB()
		self.season = season
		self.players = self.retrieve_players(min_games)
		self.player_stats = self.retrieve_player_stats()

	# Query db for list of forwards who played at least min_games games in season
	def retrieve_players(self,min_games):
		query = "SELECT player FROM (SELECT player, COUNT(*) AS GP FROM TOI{0} GROUP BY player) AS T WHERE GP>{1} ORDER BY GP DESC;".format(self.season,min_games)
		players = pd.read_sql(query,con=self.db.db)
		return players

	# Query db for date and points info for every game played by each player
	def retrieve_player_stats(self):
		player_stats = {}

		for i in range(len(self.players)):
			player = self.players.player[i]
			# Get all games played by player
			query = "SELECT gameID FROM TOI{0} WHERE player=\"{1}\";".format(self.season,player)
			gp_df = pd.read_sql(query,con=self.db.db)

			# Get number of points by player in each game
			query = "SELECT gameID, COUNT(*) AS points FROM Goals{0} WHERE (shooter=\"{1}\" OR  primaryAssist=\"{1}\" OR secondaryAssist=\"{1}\") AND period<5 GROUP BY gameID;".format(self.season,player)
			points_df = pd.read_sql(query,con=self.db.db)

			# Get date of each game played by player
			gp_tup = tuple(gp_df.gameID)
			query = "SELECT DISTINCT gameID, date FROM Games{0} WHERE gameID IN {1};".format(self.season,gp_tup)
			dates_df = pd.read_sql(query,con=self.db.db)

			ps_df = pd.merge(dates_df,points_df, on="gameID", how="left")
			ps_df = ps_df.fillna(value=0)

			player_stats[player] = ps_df

		print player_stats["DANIEL SEDIN"]
		return player_stats






if __name__ == "__main__":

	# TO SET
	season = 20152016
	min_games = 41

	pld = PlayerData(season,min_games)