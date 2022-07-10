#!/bin/bash

##Description - This script is invokved by UKCloud_transfer.py to collect
#								and transfer sample data to UKCloud.

#By: Sabri Jamal
#Date: 20191121
#Version: 1.0

###########
## Input ##
###########
pool=$1
trial_id=$2
sample_name=$3 #moldx

######################
## Static variables ##
######################
data_report_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/001.reports"
#data_analysis_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/3.analysis"
#data_analysis_path="/data/rds/DMP/DUDMP/TRANSGEN/transgen-mdx/LegacyDavros/ngs/3.analysis"
#data_fastq_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/2.fastq"
data_fastq_path="/data/rds/DMP/DUDMP/TRANSGEN/TIER2/transgen-mdx/003.Fastqs"
#destination_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud"
destination_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud/Exomes"
log_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud/XXX_TEST_AREA_XXX/logfile"
transfer_log_file="samples_ready_to_transfer.log"
transfer_log_file="$log_path/$transfer_log_file"
#uk_cloud_desination="s3://smpaeds/CMP/WES_auto_tmp/"
#uk_cloud_log_file_desintation="s3://smpaeds/CMP/"
target_data_destination=":/mnt/smpencrypted/download/CMP_AutomaticTransferPipeline/WES_auto_tmp/."
target_log_destination=":/mnt/smpencrypted/download/CMP_AutomaticTransferPipeline/."
transf_command="scp -r"
server="@sutsftpalma01v.icr.ac.uk"
user="transgen-mdx"

#Compounded vars
full_sample_name="$sample_name-$trial_id-T"
#full_sample_name=$(ls $data_fastq_path/$pool/$sample_name*R1* | rev | cut -d"/" -f1 | rev | cut -d"_" -f1)

if ls $data_fastq_path/$pool/$sample_name* 1> /dev/null 2>&1;
then
    echo "Fastq file exists, proceeeding with transfer"
else
    echo "Fastq file does not exist EXITING TRANSFER, RESOLVE"
    echo "See file for full details of all samples missing fastq data => $destination_path/fastq_missing.transfer_terminated.txt"
    printf "$pool\t$trial_id\t$sample_t\t$sample_b\n" >> $destination_path/fastq_missing.transfer_terminated.txt
    echo "Exiting..."
    exit 1
fi

folder_to_send="$destination_path/$pool.$trial_id" #Specific for exome transfer due to diff format of sending
destination_path="$destination_path/$pool.$trial_id/$full_sample_name"

#Set up transf command
send_data_cmd="$transf_command $destination_path $user$server$target_data_destination"
send_log_cmd="$transf_command $transfer_log_file $user$server$target_log_destination"


##Create destination folder
#mkdir $destination_path

###################
## Data transfer ##
###################

#Fastqs
mkdir -p $destination_path/Fastqs
cp $data_fastq_path/$pool/$full_sample_name* $destination_path/Fastqs/.

##Send files to UKCloud
#module load anaconda/3/4.4.0
#source activate UKcloud

#Send sample data to UKCloud
if [[ -d $destination_path ]];
then
	printf "\nTransferring $folder_to_send to encrypted RDS...\n"
	#s3cmd put $folder_to_send --recursive $uk_cloud_desination
    $send_data_cmd
	rm -rf $folder_to_send
	printf "\nTransfer succesful, deleting local copy $folder_to_send\n"
fi

#Send transfer log data to UKCloud
if [[ -f $transfer_log_file ]];
then
	printf "\nTransferring $transfer_log_file to encrypted RDS\n"
	#s3cmd put $transfer_log_file $uk_cloud_log_file_desintation
    $send_log_cmd
fi
