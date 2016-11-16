# Brendan Thorn - October 2016
# A brief program to simplistically test whether top NHL goal scorers (>20 goals in given 
# season) go on "hot streaks", i.e. Are they more likely to score in a game when they have
# scored in the previous game. The answer appears to be NO!

# NOTE: If you're having problems running the program, check that the config json file
# matches your system configurations, and that the db is properly named in StatsDB.py


import MySQLdb, re, time, sys, datetime, math, signal
import matplotlib.pyplot as plt
import numpy as np
import StatsDB


class PlayerData():

	def __init__(self,stats,season=20152016):
		self.db = StatsDB.StatsDB()
		self.season = season
		self.players = self.retrieve_players()
		self.player_stats = self.retrieve_player_stats(stats)

	# Query db for list of players who scored at least 20 goals in season
	def retrieve_players(self):
		query = "SELECT shooter FROM (SELECT shooter, COUNT(*) as num_goals FROM Goals{0} WHERE period<5 GROUP BY shooter ORDER BY num_goals DESC) as a WHERE num_goals>19;".format(self.season)
		temp_players = self.db.execute_query(query)
		players = []
		for player in temp_players: players.append(player[0])
		return players

	# For each player, query db for game by game count of each stat specified in stats_list
	def retrieve_player_stats(self,stats_list):

		stats_mat = np.zeros((len(self.players),82))
		player_counter = 0
		for player in self.players:
			for stat in stats_list:
				print "Working on ", stat, " for ", player
				if stat == "goals":
					# Get gameIDs for games played by player
					query = "SELECT gameID FROM TOI{0} WHERE player=\"{1}\" AND total>200 ORDER BY gameID;".format(self.season,player)
					temp_ids = self.db.execute_query(query)
					gids = []
					for gid in temp_ids: gids.append(int(gid[0]))
					# Get gameIDs,counts for games where player registered goal
					query = "SELECT gameID, COUNT(*) FROM Goals{0} WHERE shooter=\"{1}\" AND period<5 GROUP BY gameID ORDER BY gameID;".format(self.season,player)
					temp_counts = self.db.execute_query(query)
					gid_counter = 0
					temp_counter = 0
					for gid in gids:
						if gid==int(temp_counts[temp_counter][0]):
							stats_mat[player_counter,gid_counter] = int(temp_counts[temp_counter][1])
							if temp_counter == len(temp_counts)-1: break
							temp_counter += 1
						gid_counter += 1
			stats_mat[player_counter,len(gids):] = -1
			player_counter += 1
		return stats_mat


class EventCorrelations():

	def __init__(self,player_data):
		self.pd = player_data

	def compute_goal_frequencies(self):
		ng_count = 0
		g_count = 0
		ng_ng_count = 0
		ng_g_count = 0
		g_ng_count = 0
		g_g_count = 0
		player_counter = 0
		for player in self.pd.players:
			player_ng_count = 0
			player_g_count = 0
			player_ng_ng_count = 0
			player_ng_g_count = 0
			player_g_ng_count = 0
			player_g_g_count = 0
			mat = self.pd.player_stats[player_counter]
			for game_counter in range(1,82):
				if mat[game_counter] == -1: break

				if mat[game_counter-1] == 0 and mat[game_counter] == 0:
					ng_count += 1
					player_ng_count += 1
					ng_ng_count += 1
					player_ng_ng_count += 1
				elif mat[game_counter-1] == 0 and mat[game_counter] > 0:
					ng_count += 1
					player_ng_count += 1
					ng_g_count += 1
					player_ng_g_count += 1
				elif mat[game_counter-1] > 0 and mat[game_counter] == 0:
					g_count += 1
					player_g_count += 1
					g_ng_count += 1
					player_g_ng_count += 1
				elif mat[game_counter-1] > 0 and mat[game_counter] > 0:
					g_count += 1
					player_g_count += 1
					g_g_count += 1
					player_g_g_count += 1
			print "After ", player_ng_count, " games in which ", player, " did not score, he did not score in the following game ", player_ng_ng_count, " times."
			print "After ", player_ng_count, " games in which ", player, " did not score, he scored in the following game ", player_ng_g_count, " times."
			print "After ", player_g_count, " games in which ", player, " did score, he did not score in the following game ", player_g_ng_count, " times."
			print "After ", player_g_count, " games in which ", player, " did score, he scored in the following game ", player_g_g_count, " times."
			print player, ": NG->G: ", float(player_ng_g_count)/float(player_ng_count), " G->G: ", float(player_g_g_count)/float(player_g_count)
			player_counter += 1

		print "After ", ng_count, " games in which players did not score, they did not score in the following game ", ng_ng_count, " times."
		print "After ", ng_count, " games in which players did not score, they scored in the following game ", ng_g_count, " times."
		print "After ", g_count, " games in which players did score, they did not score in the following game ", g_ng_count, " times."
		print "After ", g_count, " games in which players did score, they scored in the following game ", g_g_count, " times."
		print "NG->G: ", float(ng_g_count)/float(ng_count), " G->G: ", float(g_g_count)/float(g_count)



if __name__ == "__main__":

	# TO SET:
	season = 20152016
	stats = ["goals"]


	pd = PlayerData(stats,season)
	ec = EventCorrelations(pd)
	ec.compute_goal_frequencies()


