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
		self.player_stats = self.retrieve_player_stats()

	# Query db for list of forwards who played at least min_games games in season
	def retrieve_players(self,min_games):
		query = "SELECT player FROM (SELECT player, COUNT(*) AS GP FROM TOI{0} GROUP BY player) AS T WHERE GP>{1} ORDER BY GP DESC;".format(self.season,min_games)
		elig_players = pd.read_sql(query,con=self.db.db)

		query = "SELECT name, weight FROM PlayerRatings{0} WHERE position=\"C\" OR position=\"LW\" OR position=\"RW\";".format(self.season)
		forwards = pd.read_sql(query,con=self.db.db)

		players = forwards.loc[forwards["name"].isin(elig_players["player"])]
		players = players.reset_index()
		del players["index"]
		players.columns = ["player","weight"]
		return players

	# Query db for date and points info for every game played by each player
	def retrieve_player_stats(self):
		player_stats = {}
		player_weights = {}

		for i in range(len(self.players)):
			player = self.players.player[i]
			print "Getting stats from DB for ", player

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

		return player_stats


class StatComputations():

	def __init__(self,player_data,fatigue_days):
		self.player_data = player_data
		self.fat_days = fatigue_days
		self.fatigue_dict = self.compute_fatigue()

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

	# Separate fatigue stats based on player weights
	def fatigue_by_weight(self,weight_bounds):
		players = self.player_data.players
		players_by_weight = []
		fatigue_by_weight = []

		for i in range(1,len(weight_bounds)):
			#print "\nWeight class ", weight_bounds[i-1], " to ", weight_bounds[i], "\n"
			plyrs_wt_df = players.query('(weight >= @weight_bounds[@i-1]) & (weight < @weight_bounds[@i])')
			players_by_weight.append(plyrs_wt_df)
			#print plyrs_wt_df

			count = 0
			for player in plyrs_wt_df.player:
				if count == 0:
					fat_wt_df = self.fatigue_dict[player]
				else:
					fat_wt_df = fat_wt_df.append(self.fatigue_dict[player])
				count +=1
			fatigue_by_weight.append(fat_wt_df)
			#print fat_wt_df

		return fatigue_by_weight, players_by_weight


	def make_plots(self,fatigue_by_weight,agg_by_weight,agg_by_weight_err,weight_bounds):
		if not type(fatigue_by_weight) is list:
			fatigue_by_weight = [fatigue_by_weight]
		if not type(agg_by_weight) is list:
			agg_by_weight = [agg_by_weight]

		# Set min and max number of games in last self.fat_days you want to consider for stats
		if self.fat_days < 7:
			min_games = 1
			max_games = 3
		elif self.fat_days < 10:
			min_games = 2
			max_games = 5
		else:
			min_games = 3
			max_games = math.floor(self.fat_days/2)

		x_string = "Games played in previous ", self.fat_days, " days"
		y_string = "Points per game average by player"

		count = 0
		for fbw,abw,abw_err in zip(fatigue_by_weight,agg_by_weight,agg_by_weight_err):
			plt.figure(count+1)
			# Plot individual player points
			x1 = fbw.index.values
			y1 = fbw["points"].values
			# Select and plot aggregated means for values between min_games and max_games
			abw_sel = abw.query('(density >= @min_games) & (density <= @max_games)')
			x2 = abw_sel.index.values
			y2 = abw_sel["points"].values
			# Select values between min_games and max_games for individual players, plot best fit
			fbw_sel = fbw.query('(density >= @min_games) & (density <= @max_games)')
			x3 = np.unique(x1)
			y3 = np.poly1d(np.polyfit(fbw_sel.index.values, fbw_sel["points"].values, 1))(np.unique(x3))

			# Create plot
			plt.plot(x1,y1,'bx',x2,y2,"ro",x3,y3,"g")
			plt.hold(True)
			# Add error bars
			abw_err_sel = abw_err.query('(density >= @min_games) & (density <= @max_games)')
			plt.errorbar(x2,y2,yerr=abw_err_sel["points"].values,fmt='ro')
			# Add some labels and formatting
			plt.xlim([min(x2)-.5,max(x2)+.5])
			plt.ylim([0,1.5])
			title_string = self.player_data.season, " Players weighing between ", weight_bounds[count], "lbs and ", weight_bounds[count+1], "lbs"
			plt.xlabel(x_string)
			plt.ylabel(y_string)
			plt.title(title_string)
			leg_str = "Linear Fit: " + str(np.poly1d(np.polyfit(fbw_sel.index.values, fbw_sel["points"].values, 1)))
			plt.figtext(.5,.75,leg_str)
			plt.hold(False)

			count += 1
		plt.show()


	# Group fatigue stats (points) in each weight class by game density 
	def agg_by_weight(self,fatigue_by_weight):
		if not type(fatigue_by_weight) is list:
			fatigue_by_weight = [fatigue_by_weight]

		agg_by_weight = []
		agg_by_weight_std = []
		for fbw in fatigue_by_weight:
			agg_df = fbw.groupby(fbw.index).mean()
			agg_std = fbw.groupby(fbw.index).std()
			agg_std_err = agg_std.divide(np.sqrt(fbw.groupby(fbw.index).count()))
			agg_by_weight.append(agg_df)
			agg_by_weight_std.append(agg_std_err)
		return agg_by_weight, agg_by_weight_std


	# Computes number of games played since prev_date, not including game on cur_date
	def compute_game_density(self,prev_date,cur_date,player_stats):
		# Count games that occurred >= prev_date and < cur_date
		num_games = player_stats.query('(date >= @prev_date) & (date < @cur_date)').count()["date"]
		density = 1.*num_games
		#density = 1.*num_games/self.fat_days
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
	try: 
		season = int(sys.argv[1])
	except:
		season = 20152016

	try:
		fatigue_days = int(sys.argv[2])
	except:
		fatigue_days = 14
	min_games = 61
	weight_bounds = [140,182,195,203,210,220,270]


	pld = PlayerData(season,min_games)
	sc = StatComputations(pld,fatigue_days)
	fbw,pbw = sc.fatigue_by_weight(weight_bounds)
	abw, abw_err = sc.agg_by_weight(fbw)
	sc.make_plots(fbw,abw,abw_err,weight_bounds)

