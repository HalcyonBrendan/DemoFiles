# Brendan Thorn - November 2016
# A program to test the correlation between player size and fatigue, to the
# extent that it shows up in time periods with high game densities. Would ideally
# use player age as well, but don't currently have that available.

# NOTE: If you're having problems running the program, check that the config json file
# matches your system configurations, and that the db is properly named in StatsDB.py

import MySQLdb, re, time, sys, math, signal
from datetime import date, timedelta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import StatsDB


class PlayerData():

	def __init__(self,season=20152016,min_games=41):
		self.db = StatsDB.StatsDB()
		self.season = season
		self.players = self.retrieve_players(min_games)
		self.player_stats, self.player_weights = self.retrieve_player_stats()

	# Query db for list of forwards who played at least min_games games in season
	def retrieve_players(self,min_games):
		query = "SELECT player FROM (SELECT player, COUNT(*) AS GP FROM TOI{0} GROUP BY player) AS T WHERE GP>{1} ORDER BY GP DESC;".format(self.season,min_games)
		all_players = pd.read_sql(query,con=self.db.db)

		query = "SELECT name FROM PlayerRatings{0} WHERE position=\"C\" OR position=\"LW\" OR position=\"RW\";".format(self.season)
		forwards = pd.read_sql(query,con=self.db.db)

		players = all_players.loc[all_players["player"].isin(forwards["name"])]
		players = players.reset_index()
		return players

	# Query db for date and points info for every game played by each player
	def retrieve_player_stats(self):
		player_stats = {}
		player_weights = {}

		for i in range(len(self.players)):
			player = self.players.player[i]
			print "Getting stats from DB for ", player
			# Get player weight
			query = "SELECT weight FROM PlayerRatings{0} WHERE name=\"{1}\";".format(self.season,player)
			pw_df = pd.read_sql(query,con=self.db.db)
			player_weights[player] = pw_df

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

		return player_stats, player_weights


class StatComputations():

	def __init__(self,player_data,fatigue_days):
		self.player_data = player_data
		self.fat_days = fatigue_days
		self.fatigue = self.compute_fatigue()
		self.fatigue_agg_df = self.aggregate_fatigue()

	def compute_fatigue(self):
		print ""
		fatigue_dfs = {}
		fatigue_avgs = {}
		players = self.player_data.players
		player_dfs = self.player_data.player_stats
		# Loop through players
		for player in players.player:
			print "Computing fatigue stats for ", player
			player_stats = player_dfs[player]
			fatigue_df = player_stats.copy()
			fatigue_df["density"] = 0

			game_count = 0
			for game_date in player_stats.date:
				# Get earliest date in fatigue period
				prev_date = self.compute_date(game_date)
				# Count number of games played since then
				fatigue_df.loc[game_count,"density"] = self.compute_game_density(prev_date,game_date,player_stats)
				game_count += 1

			fatigue_dfs[player] = fatigue_df

			# Average p/g for each game_density bin
			fatigue_avg = fatigue_df.groupby(["density"]).mean()
			del fatigue_avg["gameID"]
			del fatigue_avg["date"]

			fatigue_avgs[player] = fatigue_avg

		return fatigue_avgs


	def build_plots(self):
		plt.figure()
		plt.plot(self.fatigue_agg_df.index.values,self.fatigue_agg_df["points"].values,'bx')
		plt.show()

	# Combine dictionary of fatigue_avg dfs into single df
	def aggregate_fatigue(self):
		agg_df = pd.DataFrame()
		players = self.player_data.players

		count = 0
		for player in players.player:
			print player
			if count == 0:
				agg_df = self.fatigue[player]
			else:
				agg_df = agg_df.append(self.fatigue[player])
			count += 1
		return agg_df

	# Computes number of games played since prev_date, not including game on cur_date
	def compute_game_density(self,prev_date,cur_date,player_stats):
		# Count games that occurred >= prev_date and < cur_date
		num_games = player_stats.query('(date >= @prev_date) & (date < @cur_date)').count()["date"]
		density = 1.*num_games/self.fat_days
		return density

	# Given current date, computes date that occurred self.fat_days earlier
	# i.e. Let cur_date=20160101, self.fat_days=10. Then prev_date = 20151222.
	def compute_date(self,cur_date):
		cur_date = str(cur_date)
		cur_date_obj = date(int(cur_date[0:4]),int(cur_date[4:6]),int(cur_date[6:8]))
		prev_date = cur_date_obj-timedelta(self.fat_days)
		prev_date = int(prev_date.strftime("%Y%m%d"))
		return prev_date



if __name__ == "__main__":

	# TO SET
	season = 20152016
	min_games = 70
	fatigue_days = 14


	pld = PlayerData(season,min_games)
	sc = StatComputations(pld,fatigue_days)
	sc.build_plots()

