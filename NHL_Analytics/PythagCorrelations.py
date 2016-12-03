# Brendan Thorn - November 2016

# A file to find optimal exponent value, d, for "pythagorean wins" theorom for hockey.
# win % = GF^d/(GF^d + GA^d)
# where GF = team goals for, GA = team goals against, and in both cases empty net and shootout goals will not be counted.
#
# Currently define "optimal" as exponent that maximizes R^2 coeff, or, equivalenty, minimizes MSE between true number of
# wins and predicted number of wins by pythag theorem.

import MySQLdb, re, time, sys, math, signal
from datetime import date, timedelta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats.stats import pearsonr
from sklearn.metrics import r2_score
import StatsDB


class TeamStats():

	def __init__(self, season):
		self.db = StatsDB.StatsDB()
		self.season = season
		self.stats, self.team_GPs = self.retrieve_stats()

	def retrieve_stats(self):
		query = """SELECT A.team AS team, A.GF AS GF, B.GA AS GA, C.Wins AS Wins FROM (SELECT team, COUNT(*) AS GF FROM Goals{0} WHERE period<5 AND distance<70 GROUP BY team) AS A JOIN (SELECT opponent, COUNT(*) AS GA FROM Goals{0} WHERE period<5 AND distance<70 GROUP BY opponent) AS B ON A.team = B.opponent JOIN (SELECT winner, COUNT(*) AS Wins FROM Games{0} WHERE winner=team GROUP BY winner) AS C ON A.team = C.winner ORDER BY A.team""".format(self.season)
		goal_stats = pd.read_sql(query,con=self.db.get_connection())
		query = """SELECT COUNT(*) FROM Games{0} WHERE team="MTL";""".format(self.season)
		team_GPs = int(self.db.execute_query(query)[0][0])
		return goal_stats, team_GPs


class PythagCorrelations():

	def __init__(self, season, team_stats):
		self.stats = team_stats.stats
		self.team_GPs = team_stats.team_GPs
		self.season = season
		self.opt_r2_exp = 0
		self.opt_mse_exp = 0
		self.pc = self.compute_pyth_corrs()
		self.plot_corrs()

	def compute_pyth_wins(self,d):
		pyth_wins = self.team_GPs * self.stats.GF**d/(self.stats.GF**d + self.stats.GA**d)
		return pyth_wins

	def compute_pyth_corrs(self):
		exponents = np.arange(1,3.01,.01)
		pyth_corrs = pd.DataFrame({"Expon": exponents,"R2": np.zeros(len(exponents)),"MSE": np.zeros(len(exponents))})
		pyth_corrs = pyth_corrs.set_index("Expon")
		pyth_stats = self.stats

		max_r2 = -1
		min_mse = 1000000000

		for d in exponents:
			pyth_wins = self.compute_pyth_wins(d)
			pyth_stats["Pyth_Wins"] = pyth_wins
			#pyth_corrs.loc[d]["Correl"] = pearsonr(self.stats.Wins,pyth_wins)[0]
			r2_val = r2_score(self.stats.Wins,pyth_wins)
			if r2_val > max_r2:
				max_r2 = r2_val
				self.opt_r2_exp = d
			pyth_corrs.loc[d]["R2"] = r2_val
			mse_val = ((self.stats.Wins-pyth_wins)**2).mean()
			if mse_val < min_mse:
				min_mse = mse_val
				self.opt_mse_exp = d
			pyth_corrs.loc[d]["MSE"] = mse_val
			#print pyth_corrs.loc[d]["R2"]
		return pyth_corrs

	def plot_corrs(self):
		plt.figure(1)
		plt.plot(self.pc.index.values,self.pc["R2"].values)
		plt.xlabel("Pythag Exponent")
		plt.ylabel("R2 Coeff")
		title_str = "{0} - Optimal Exponent: {1}".format(self.season,self.opt_r2_exp)
		plt.title(title_str)
		plt.xlim([.5, 3.5])
		plt.ylim([min(self.pc["R2"].values)-.03, max(self.pc["R2"].values)+.03])
		#plt.figure(2)
		#plt.plot(self.pc.index.values,self.pc["MSE"].values)
		#plt.xlabel("Pythag Exponent")
		#plt.ylabel("MSE")
		#title_str = "{0} - Optimal Exponent: {1}".format(self.season,self.opt_mse_exp)
		#plt.title(title_str)
		plt.show()


if __name__ == "__main__":
	# TO SET
	if len(sys.argv) > 1:
		try: season = int(sys.argv[1])
		except: 
			season = 20152016
			print "Season set to ", season, " by default. Include season in yyyyyyyy format as command line arg to change."
	else:	
		season = 20152016
		print "Season set to ", season, " by default. Include season in yyyyyyyy format as command line arg to change."
	
	ts = TeamStats(season)
	pc = PythagCorrelations(season,ts)