#!/bin/env python

#################
## Description ##
#################
#	- Python script for automation of data transfer to UKCloud by targeting
#	  specific samples for a given project supplied through the YAML
#	  config file. Originally developed for the StratMed PAEDs project.

###########
## Input ##
###########
  # Input given at call of script.
      # - YAML config file

#####################
## Related scripts ##
#####################
#	- transfer_script.sh => Collects data for a given sample and uploads to
# 				UKCloud together with transfer log generated by
#				this script.

        #By: Sabri Jamal
        #Date: 20191121
	#Version: 1.0

##------------------------------------------------------------------------------------------------------------------------------------------##


import os
import sys
import getopt
import pdb
import re
import subprocess as subp
import datetime
import yaml
import pdb

class UKCloud(object):
	##Class attribute
	config = None

	def __init__(self, config_file):
		#Instanciation vars
		self.config_file = config_file
		self.config = self.load_config(self.config_file)

	#Reads the yaml config file
	def load_config(self, config_file):
		with open(config_file, "r") as IN_config:
			UKCloud.config = yaml.load(IN_config)

	#Function load succesfully transferred samples into dict. Dict is used
	#to determine which samples to skip within func write_dict_to_file
	def load_file_as_2lvl_nested_dict(self, succesful_transfers_file):
		glob_pool_dict = {}

		#Parse samples succesfully transferred to UKCloud
		try:
			with open(succesful_transfers_file, "r") as succ_transf_pool_IN:
				for line in succ_transf_pool_IN:
					line = line.rstrip()
					match = re.split("\t", line)
					pool_id = match[0]
					trial_id = match[1]
					tumour = match[2]
					germline = match[3]


					if(pool_id not in glob_pool_dict):
						glob_pool_dict[pool_id] = {tumour : germline}
					elif(pool_id in glob_pool_dict and tumour not in glob_pool_dict[pool_id]):
						glob_pool_dict[pool_id][tumour] = germline
					elif(pool_id in glob_pool_dict and tumour in glob_pool_dict[pool_id]):
						prompt = "{ts} - WARNING; Duplicate entry for tumour {tumour} sample in pool {pool_id}".format(ts=str(datetime.datetime.now()), tumour=tumour, pool_id=pool_id)
						print(prompt)
		except FileNotFoundError:
			prompt = "{ts} - WARNING; Log file tracking succesfuly transferred samples not found, no samples will be skipped.".format(ts=str(datetime.datetime.now()))
			print(prompt)

		return(glob_pool_dict)

	##Parses all sample sheets selectively choosing sample sheets containing
	# StratMed PAED (SMP) suffix using a global grep for primary filtering
	def parse_sample_sheets(self):

		##Instantiate static variables
		sample_sheet_suffix = UKCloud.config['sample-sheet']['suffix']
		sample_sheet_dir = UKCloud.config['file_system_objects']['sample_sheet_path']

		glob_ss_dict = {} #holds all sample sheets (nested)

		##Body
		direc_listing = os.listdir(sample_sheet_dir)
		for fso in direc_listing:

			#Skip if reading non target sample sheets
			if(fso.find("secondaryanalyses") >= 0 or fso.find("demultiplex") >= 0):
				continue

			fso_abs_path = os.path.join(sample_sheet_dir, fso)
			ss_dict = {} #holds one sample sheet stored in nested dict glob_ss_dict

			if( os.path.isdir(fso_abs_path) ):
				continue

			match = re.search(sample_sheet_suffix, fso)
			if(match):

				##Check sample sheet contains SMPaed sample
				cmd = 'grep "SMP" '
				cmd = cmd + fso_abs_path
				grep = subp.Popen(cmd, stdout=subp.PIPE, shell=True)

				#Decode byte & parse sample sheet
				if(grep.stdout.readline().decode("UTF-8") != ""):

					with open(fso_abs_path, "r") as ss_IN:
						meta = True
						header = True
						ss_dict = {}

						for line in ss_IN:

							#Skip empty lines
							if(not line.strip()):
								continue

							line = line.rstrip()

							#TODO# Future improvement - To add logic to handle
							# hashed out lines. See top head of script for more
							# details
							# sample sheet
							#if(line.startswith("#Pool")):
							#	meta = False
							#elif(line.startswith("#")):
							#	meta = True
							#else:
							#	meta = False

							#Logic to detect meta data or commented lines in
							#sample sheet
							if(line.startswith("#")):
								meta = True
							else:
								meta = False

							#Parse non meta data
							if(meta):
								continue
							else:
								#Store header data
								if(header):
									header_array = re.split(",", line)
									header = False
								else:
									data_list = re.split(",", line)

								#Store per sample sheet data in dict
								for i in range(0, len(header_array)):
									ss_header = header_array[i].lower()
									if(ss_header not in ss_dict):
										ss_dict[ss_header] = []
									else:
										prev_list = ss_dict[ss_header]

										##Debugging
										try:
											prev_list.append(data_list[i])
											ss_dict[ss_header] = prev_list
										except IndexError as e:
											prompt="{ts} - WARNING; Number of columns don't match with the data for sample sheet {fso}".format(fso=fso, ts=str(datetime.datetime.now()))
											print(prompt)


			#Store each sample sheet dict in nested dict
			if(fso not in glob_ss_dict):
				glob_ss_dict[fso] = ss_dict
			else:
				prompt = "{ts} - WARNING; Duplicate sample sheet found for {fso}".format(fso=fso, ts=str(datetime.datetime.now()))
				print(prompt)

		return (glob_ss_dict)


	##Writes the returned dict object from parse_sample_sheets to a file
	# containing new samples to be scanned for sending.
	def write_dict_to_file(self, glob_ss_dict):
		##Instantiate static variables
		allowed_panels = [ UKCloud.config['panels']['paediatric'], UKCloud.config['panels']['exome'] ]
		bed_col = UKCloud.config['sample-sheet']['bedfile_col']
		seq_pool_id = [ UKCloud.config['sample-sheet']['pool_id_col'] ]
		sample_name_col = [ UKCloud.config['sample-sheet']['sample_name_col'] ]
		sample_pair_name_col = [ UKCloud.config['sample-sheet']['sample_pair_name_col'] ]
		wild_card_col = [ UKCloud.config['sample-sheet']['wild_card_col'] ]
		sample_type = [ UKCloud.config['sample-sheet']['sample_type'] ]
		ready_to_send = UKCloud.config['log_files']['transfer_log']
		output_path = UKCloud.config['file_system_objects']['logfile_dest_path']

		##Instantiate dynamic variables
		pool_id_list = []
		moldx_sample_t_list = []
		moldx_sample_b_list = []
		trial_id_list = []

		##Set full paths for log files
		ready_log_abs_path = os.path.join(output_path, ready_to_send)

		##Store all pools previously transferred to UKCloud
		if(os.path.exists(ready_log_abs_path)):
			succ_transf_dict = self.load_file_as_2lvl_nested_dict(ready_log_abs_path)
		else:
			prompt = "{ts} - WARNING; Log file tracking succesfuly transferred samples not found, no samples will be skipped.".format(ts=str(datetime.datetime.now()))
			print(prompt)

		##Create output file with header if doesn't exist
		if(not os.path.exists(ready_log_abs_path)):
			header = "Pool\tTrial_ID\tTumour\tBaseline\tCheck1\tDate_Check1\tCheck2\tGermline\tDate_Germline\tUKCloud\tDate_UKCloud\tExome_UKCloud\n"
			with open( os.path.join(ready_log_abs_path), "w") as ready_IN:
				ready_IN.write(header)

		##Loop to access sample sheet dict for each pool
		for pool, ss_dict in glob_ss_dict.items():

			##Skip empty sample sheets that were picked up to noto have SMPAEDs
			#sample through global
			if(len(ss_dict) == 0):
				continue

			#Skip germline sample sheets ending with suffix G
			if(pool.split(".")[0].endswith("G")):
				continue

			ss_dict_samp_name_list = ss_dict[sample_name_col[0]].copy()

			#Reset variables
			del_tumour_inds = []
			del_germline_inds = []
			del_inds = []
			target_ind = []
			tumour_ind = []

			#Extract pool id from sample sheet
			pool_id = pool.split(".")[0]

			try:
				# Controls samples to only be logged once in transfer log file
				if(pool_id in succ_transf_dict.keys()):
					#Compare tumour/germline id from file with dict and delete entry
					# if exists
					for tumour, germline in succ_transf_dict[pool_id].items():
						for sample in ss_dict_samp_name_list:
							if( sample.find(tumour) >= 0):
								del_tumour_inds.append(ss_dict_samp_name_list.index(sample))

							if( sample.find(germline) >= 0):
								del_germline_inds.append(ss_dict_samp_name_list.index(sample))

					##Delete entries for tumour & germline samples succesfuly transferred
					if( len(set(del_tumour_inds) & set(del_germline_inds)) == 0 ):
						del_inds = del_tumour_inds + del_germline_inds
						for column_key, value_list in ss_dict.items():
							for index in sorted(del_inds, reverse=True):

								del ss_dict[column_key][index]
					else:
						prompt = "{ts} - WARNING; Possible ambigous match was found when searching moldx ID for tumour or germline in sample sheet {ss_sheet}. Skipping reading of entire sample sheet {ss_sheet}".format(ss_sheet=pool, ts=str(datetime.datetime.now()))
						print(prompt)
						continue #Skip

			except UnboundLocalError:
				prompt = "{ts} - WARNING; Log file tracking succesfuly transferred samples not found, no samples will be skipped.".format(ts=str(datetime.datetime.now()))
				print(prompt)


			##Check that analysed on PAEDs panel to target only SMPaeds sample
			#second level of security
			if(allowed_panels[0] not in ss_dict[bed_col] or allowed_panels[1] not in ss_dict[bed_col]):
				continue #skip non target (PAED) samples. Covers WES PAEDs
						 #as well
			else:
				#Store header as list by converting from dict.key obj to
				#list obj to access index
				header_array = [header for header in ss_dict.keys()]

				#Locate indexes for target "columns" in sample sheet
				if(sample_name_col[0] in header_array and seq_pool_id[0] in header_array and sample_pair_name_col[0] in header_array):
					samp_name_ind = header_array.index(sample_name_col[0])
					pool_id_ind = header_array.index(seq_pool_id[0])
					gatk_grp_ind = header_array.index(sample_pair_name_col[0])

				##Locate indexes for target samples containing right trial ID
				target_ind = [i for i, sample in enumerate(ss_dict[sample_name_col[0]]) if(re.search("-SMP\d+-", sample))]

				##Locate indexes for all tumour samples
				# NOTE! Exomes can be sequenced with either only baseline or tumour condition can't wait for match!
				tumour_ind = [i for i, samp_type in enumerate(ss_dict[sample_type[0]]) if(samp_type.lower() == "tumour") ]

				##Locate indexes for all exomes
				# NOTE! Add case specific name for exome and keep current set up in place
				# NOTE! One example of location to add conditional to skip sample sheet with 'other' column set to qc_run (catch exception though!!)
				exome_ind = [i for i, exome_bed in enumerate(ss_dict[allowed_panels[1]]) if(allowed_panels.lower() == "idtExome".lower() )]

				##Select only tumour samples i.e. find intersect from sample
				#sheet to avoid duplicates in ready to transfer file
				target_ind = set(target_ind) & set(tumour_ind)

				target_ind_exome = set(target_ind) & set(exome_ind)

			##Fetch panel data to be written to ready to transfer file
			if(len(target_ind) != 0):
				for ind in target_ind:
					sample_moldx_t = ss_dict.get(sample_name_col[0])[ind]
					sample_moldx_b = ss_dict.get(sample_pair_name_col[0])[ind]
					sample_trial_id =  ss_dict.get(sample_name_col[0])[ind]
					match_moldx_t = re.search("(\d+)-SMP\d+", sample_moldx_t)
					match_moldx_b = re.search("(\d+)-SMP\d+", sample_moldx_b)
					match_trial_id = re.search("\d+-(SMP\d+)",sample_trial_id)

					if(match_moldx_t and match_moldx_b and match_trial_id):
						pool_id_list.append(ss_dict.get(seq_pool_id[0])[ind])
						moldx_sample_t_list.append(match_moldx_t.group(1))
						moldx_sample_b_list.append(match_moldx_b.group(1))
						trial_id_list.append(match_trial_id.group(1))
					else:
						prompt="{ts} - WARNING; Tumour {tumour}, germline {germline} or trial id {trial_id} does not match target project name structure".format(tumour=sample_moldx_t, germline=sample_moldx_b, trial_id=sample_trial_id, ts=str(datetime.datetime.now()))

			##Fetch exome data to be written to ready to transfer file
			# NOTE! ANOTHER example of location to add conditional to skip sample sheet with 'other' column set to qc_run (catch exception though!!)
			if(len(target_ind_exome) != 0):
				for ind in target_ind_exome:
					sample_check_if_qc = ss_dict.get(wild_card_col[0])[ind]

					##Ignore duplicate analysis due to qc
					if(sample_check_if_qc == "qc_run"):
						continue

					sample_moldx_generic = ss_dict.get(sample_name_col[0])[ind]
					sample_tag_generic = ss_dict.get(sample_type[0])[ind]
					match_moldx_generic = re.search("(\d+)-SMP\d+", sample_moldx_generic)
					match_trial_id = re.search("\d+-(SMP\d+)",sample_moldx_generic)

					if(match_moldx_generic and match_trial_id):
						pool_id_list.append(ss_dict.get(seq_pool_id[0])[ind])
						trial_id_list.append(match_trial_id.group(1))

						# NOTE! This is where generic name needs to be tested if either normal or tumour by looking at tag column in SS
						if(sample_tag_generic.lower() == "tumour" or sample_tag_generic.lower() == "tumor"):
							moldx_sample_t_list.append(match_moldx_generic.group(1))
						elif(sample_tag_generic.lower() == "normal"):
							moldx_sample_b_list.append(match_moldx_b.group(1))
					else:
						prompt="{ts} - WARNING; Exome sample name {tumour} or trial id {trial_id} does not match target project name structure".format(tumour=sample_moldx_t, trial_id=sample_trial_id, ts=str(datetime.datetime.now()))

		##Write data to ready to transfer file
		with open( os.path.join(ready_log_abs_path), "a") as ready_IN:
			equal_tot_length = len(pool_id_list) #used as template as all should be equal sized
			if( len(pool_id_list) == len(moldx_sample_t_list) == len(moldx_sample_b_list) == len(trial_id_list) and equal_tot_length > 0 ):
				for i in range(0, equal_tot_length):
					ready_IN.write(pool_id_list[i] + "\t" + trial_id_list[i] + "\t" + moldx_sample_t_list[i] + "\t" + moldx_sample_b_list[i] + "\n")

	##Picks up the ready to transfer file created by write_dict_to_file.
	# It prepares a subprocess call for each line that is scanned to be ready for
	# transferring after confirming that checker 2 has been done. It will also update
	# the log file written by write_dict_to_file.
	#NOTE! continue from here if needed!
	def transfer_UKCloud(self):
		##Instantiate static variables
		analysis_folder_root_path = UKCloud.config['file_system_objects']['analysis_folder_root_path']
		analysis_reports_folder = UKCloud.config['file_system_objects']['analysis_reports_folder']
		uk_cloud_transfer_script = UKCloud.config['file_system_objects']['uk_cloud_transfer_script']
		ready_to_transfer_file = UKCloud.config['log_files']['transfer_log']
		output_path = UKCloud.config['file_system_objects']['logfile_dest_path']
		header = True
		germline_pool_suffix = "G"

		##Set full paths for logfiles
		ready_to_transfer_file =  os.path.join(output_path, ready_to_transfer_file)

		ready_to_transfer_file_tmp = ready_to_transfer_file + ".tmp"
		new_line = "" ##Line to store updated data

		##Create output file with header if doesn't exist
		if(not os.path.exists(ready_to_transfer_file_tmp)):
			header_str = "Pool\tTrial_ID\tTumour\tBaseline\tCheck1\tDate_Check1\tCheck2\tGermline\tDate_Germline\tUKCloud\tDate_UKCloud\n"
			with open( os.path.join(ready_to_transfer_file_tmp), "w") as ready_IN:
				ready_IN.write(header_str)

		with open(ready_to_transfer_file_tmp, "a") as ready_OUT:
			with open(ready_to_transfer_file, "r") as ready_IN:
				for line in ready_IN:

					#Skip header
					if(header):
						header = False
						continue

					#Read data
					line = line.rstrip()
					match = re.split("\t", line)
					pool_id = match[0]
					trial_id = match[1]
					sample_id_t = match[2]
					sample_id_b = match[3]
					new_line = pool_id + "\t" + trial_id + "\t" + sample_id_t + "\t" + sample_id_b

					#Set full sample name & absolute path to reports
					full_sample_name_t = sample_id_t + "-" + trial_id
					full_sample_name_b = sample_id_b + "-" + trial_id
					germline_pool_id = pool_id + "G"
					report_abs_path_somatic = os.path.join(analysis_folder_root_path, pool_id, analysis_reports_folder)
					report_abs_path_germline = os.path.join(analysis_folder_root_path, germline_pool_id, analysis_reports_folder)

					##Attempt to set dyanmic variables related to samples checked or
					# transferred. If values are set to NaN set the boolean value to false
					try:
						check1 = match[4]
						if(check1 == "NaN"):
							check1 = False

					except:
						prompt = "{ts} - NEW SAMPLES DETECTED; {pool_id} with tumour {tumour} & germline {germline}; Queued for UPDATE RECORD; Somatic checker 1 scan...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
						print(prompt)
						check1 = False

					try:
						check2 = match[6]
						if(check2 == "NaN"):
							check2 = False

					except:
						prompt = "{ts} - NEW SAMPLES DETECTED; {pool_id} with tumour {tumour} & germline {germline}; Queued for UPDATE RECORD; Somatic checker 2 scan...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
						print(prompt)
						check2 = False

					try:
						germline = match[7]
						if(germline == "NaN"):
							germline = False
					except:
						prompt = "{ts} - NEW SAMPLES DETECTED; for {pool_id} with germline {germline}; Queued for germline check scan...\n".format(ts=str(datetime.datetime.now()), germline=full_sample_name_b, pool_id=pool_id)
						print(prompt)
						germline = False

					try:
						uk_cloud = match[9]
						if(uk_cloud == "NaN"):
							uk_cloud = False
					except:
						prompt = "{ts} - NEW SAMPLES DETECTED; for {pool_id} with tumour {tumour} & germline {germline}; Queued for UKCloud transfer scan...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
						print(prompt)
						uk_cloud = False

					##Check if actions should be updated
					if(not check1):
						c1_bol = False
						regex_cmd_c1 = full_sample_name_t + ".*\.patient\.report\.\w+"
						regex_cmd_pr = full_sample_name_t + ".*\.patient\.report\.tsv"

						if(os.path.exists(report_abs_path_somatic)):
							for report in os.listdir(report_abs_path_somatic):

								patient_reprt = re.search(regex_cmd_pr, report)
								c1 = re.search(regex_cmd_c1, report)

								#Ensure that that regex only matches checker 1 and not patient.report.tsv
								if(not patient_reprt and c1):
									c1_bol = True

							if(c1_bol):
								check1 = True
								prompt = "{ts} - UPDATE RECORD; Somatic checker 1 complete for {pool_id} with tumour {tumour} & germline {germline} pair...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)
							else:
								prompt = "{ts} - UPDATE RECORD; Somatic checker 1 NOT complete for {pool_id} with tumour {tumour} & germline {germline} pair...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)

					if(not check2):
						c1_bol = False
						c2_bol = False
						regex_cmd_c1 = full_sample_name_t + ".*\.patient\.report\.\w+"
						regex_cmd_c2 = full_sample_name_t + ".*\.patient\.report"

						if(os.path.exists(report_abs_path_somatic)):
							for report in os.listdir(report_abs_path_somatic):

								c1 = re.search(regex_cmd_c1, report)
								c2 = re.search(regex_cmd_c2, report)

								if(not c1 and c2):
									c2_bol = True

							if(c2_bol):
								check2 = True
								prompt = "{ts} - UPDATE RECORD; Somatic checker 2 complete for {pool_id} with tumour {tumour} & germline {germline} pair...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)
							else:
								prompt = "{ts} - UPDATE RECORD; Somatic checker 2 NOT complete for {pool_id} with tumour {tumour} & germline {germline} pair...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)

					if(not germline):
						regex_cmd_c1 = full_sample_name_b + ".*\.patient\.report\.\w+"
						regex_cmd_c2 = full_sample_name_b + ".*\.patient\.report"
						regex_cmd_pr = full_sample_name_b + ".*\.patient\.report\.tsv"
						c1_bol = False
						c2_bol = False

						try:
							for report in os.listdir(report_abs_path_germline):
								patient_reprt = re.search(regex_cmd_pr, report)
								c1 = re.search(regex_cmd_c1, report)
								c2 = re.search(regex_cmd_c2, report)

								if(c1 and not patient_reprt):
									c1_bol = True

								if(c2 and not c1):
									c2_bol = True

							if(c1_bol and c2_bol):
								germline = True
								prompt = "{ts} - UPDATE RECORD; Germline checking complete for {pool_id} with germline {germline}...\n".format(ts=str(datetime.datetime.now()), germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)
							else:
								prompt = "{ts} - UPDATE RECORD; Germline checking NOT complete for {pool_id} with germline {germline}...\n".format(ts=str(datetime.datetime.now()), germline=full_sample_name_b, pool_id=pool_id)
								print(prompt)
						except:
							prompt = "{ts} - UPDATE RECORD; Germline pool {pool_id}{suffix} with germline {germline} not created yet...\n".format(ts=str(datetime.datetime.now()), germline=full_sample_name_b, pool_id=pool_id, suffix=germline_pool_suffix)


					#If data not been sent check if eligible
					if(not uk_cloud):
						if( check1 and check2 and germline ):
							input_data = [pool_id, trial_id, sample_id_t, sample_id_b]
							cmd = [uk_cloud_transfer_script] + input_data
							subp.call(cmd)
							uk_cloud = True

							prompt = "{ts} - UPDATE RECORD; UKCloud transfer complete for {pool_id} with tumour {tumour} & germline {germline} pair...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
							print(prompt)
						else:
							prompt = "{ts} - UPDATE RECORD; UKCloud transfer blocked due to somatic and germline sample checking NOT complete, please review log file for {pool_id} with tumour {tumour} & germline {germline} pair to investigate the cause...\n".format(ts=str(datetime.datetime.now()), tumour=full_sample_name_t,germline=full_sample_name_b, pool_id=pool_id)
							print(prompt)


					##Set variables to update logfile and update the file
					if(check1):
						check1 = "True"
						check1_date = str(datetime.datetime.now().date())
						new_line = str(new_line) + "\t" + check1 + "\t" + check1_date
					else:
						new_line = str(new_line) + "\t" + "NaN" + "\t" + "NaN"

					if(check2):
						check2 = "True"
						new_line = str(new_line) + "\t" + check2
					else:
						new_line = str(new_line) + "\t" + "NaN"

					if(germline):
						germline = "True"
						germline_date = str(datetime.datetime.now().date())
						new_line = str(new_line) + "\t" + germline + "\t" + germline_date
					else:
						new_line = str(new_line) + "\t" + "NaN" + "\t" + "NaN"

					if(uk_cloud):
						uk_cloud = "True"
						uk_cloud_date = str(datetime.datetime.now().date())
						new_line = str(new_line) + "\t" + uk_cloud + "\t" + uk_cloud_date
					else:
						new_line = str(new_line) + "\t" + "NaN" + "\t" + "NaN"

					ready_OUT.write(new_line + "\n")

		#Overwrite old file with updated file
		os.rename(ready_to_transfer_file_tmp, ready_to_transfer_file)

def main(argv):
	file_in = ""
	file_out = ""
	nr_arguments = 1 #Number of arguments required
	script = "UKCloud_transfer.py" #Name of script

	#Stores flags with arguments in opts (both flag in and input stored) and flags with no input in args
	try:
		opts, args = getopt.getopt(argv, "c:h", ["config_file=", "help="])
	except getopt.GetoptError: # If no argument given
		print(script + ' -c <yaml_config>')
		sys.exit(2)
	#Loop through flags (opt) and arguments (arg) from opts. Store appropriately
	for opt, arg in opts:
		if opt == '-h':
			print(script + ' -c <YAML_config>')
			sys.exit(2)
		elif opt in ("-c", "--config_file"):
			config_file = arg

	#If only in or out given print usage and error else run script
	if len(argv)/2 < nr_arguments:
		print("You submitted " + str(int(len(argv)/2)) + " arguments, expected " + str(nr_arguments))
		print('not enough arguments.... see below for run usage:')
		print(script + ' -c <yaml_config>')
		sys.exit(2)
	else:
		uk_cloud_obj = UKCloud(config_file)
		glob_sample_sheet_dict = uk_cloud_obj.parse_sample_sheets()
		uk_cloud_obj.write_dict_to_file(glob_sample_sheet_dict)
		uk_cloud_obj.transfer_UKCloud()

if __name__ == "__main__":
	main(sys.argv[1:])
