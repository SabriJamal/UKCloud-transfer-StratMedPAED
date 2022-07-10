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
sample_t=$3 #moldx
sample_b=$4 #moldx

######################
## Static variables ##
######################
data_report_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/001.reports"
data_analysis_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/3.analysis"
#data_analysis_path="/data/rds/DMP/DUDMP/TRANSGEN/transgen-mdx/LegacyDavros/ngs/3.analysis"
#data_fastq_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/2.fastq"
data_fastq_path="/data/rds/DMP/DUDMP/TRANSGEN/TIER2/transgen-mdx/003.Fastqs"
#destination_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud"
destination_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud/Panel-Relapse"
log_path="/data/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud/XXX_TEST_AREA_XXX/logfile"
transfer_log_file="samples_ready_to_transfer.log"
transfer_log_file="$log_path/$transfer_log_file"
suffix="G"
target_data_destination=":/mnt/smpencrypted/download/CMP_AutomaticTransferPipeline/Panel-Seq/."
target_log_destination=":/mnt/smpencrypted/download/CMP_AutomaticTransferPipeline/."
transf_command="scp -r"
server="@sutsftpalma01v.icr.ac.uk"
user="transgen-mdx"

#Compounded vars
full_sample_name="$sample_t-$trial_id-T"
destination_path="$destination_path/$full_sample_name"
pool_germ="$pool$suffix"

##Create destination folder
mkdir $destination_path

#Set up transf command
send_data_cmd="$transf_command $destination_path $user$server$target_data_destination"
send_log_cmd="$transf_command $transfer_log_file $user$server$target_log_destination"


###################
## Data transfer ##
###################

#Fastqs
mkdir -p $destination_path/Fastqs
cp $data_fastq_path/$pool/*$trial_id* $destination_path/Fastqs/.

#Alignments
mkdir $destination_path/Alignments
cp $data_report_path/$pool/Alignments/*$trial_id* $destination_path/Alignments/.

#CNVs
mkdir -p $destination_path/CNVs
cp -r $data_report_path/$pool/CNVs/*$trial_id*/* $destination_path/CNVs/.

#Reports
mkdir -p $destination_path/Reports/Germline
mkdir -p $destination_path/Reports/Somatic
cp $data_report_path/$pool/Variants/$sample_b-$trial_id-B/$sample_t-$trial_id-T.mutation.report $destination_path/Reports/Somatic/.
cp $data_report_path/$pool_germ/Variants/$sample_b-$trial_id-B/$sample_b-$trial_id-B.mutation.report $destination_path/Reports/Germline/.
cp $data_report_path/$pool/Reports/$sample_t-$trial_id-T.patient.report $destination_path/Reports/Somatic/.
cp $data_report_path/$pool_germ/Reports/$sample_b-$trial_id-B.patient.report $destination_path/Reports/Germline/.
cp $data_report_path/$pool/SVs/$sample_b-$trial_id-B/$sample_t-$trial_id-T.SV.report $destination_path/Reports/Somatic/.
cp $data_report_path/$pool/CNVs/$sample_t-$trial_id-T/$sample_t-$trial_id-T.cnv.report $destination_path/Reports/Somatic/.

#SVs
mkdir -p $destination_path/SVs/Manta_SCRATCH $destination_path/SVs/Manta_RDS
cp -r $data_analysis_path/$pool/SVs/AnnotSV/*$trial_id*-T/* $destination_path/SVs/Manta_SCRATCH/.
cp -r $data_report_path/$pool/SVs/*$trial_id*-T/* $destination_path/SVs/Manta_RDS/.

##Remove intermediary SV files
#rm $destination_path/SVs/Manta/*[wW]orkflow*
#rm -rf $destination_path/SVs/Manta/workspace

#Stats
mkdir $destination_path/Stats
cp $data_report_path/$pool/Stats/*$trial_id* $destination_path/Stats/.

#Variants (Raw VCF)
mkdir -p $destination_path/Variants/Germline
mkdir -p $destination_path/Variants/Somatic
cp $data_report_path/$pool/Variants/$sample_b-$trial_id-B/SNV.$sample_t-$trial_id-T.vcf $destination_path/Variants/Somatic/.
cp $data_report_path/$pool_germ/Variants/$sample_b-$trial_id-B/GATK*$trial_id-B.vcf $destination_path/Variants/Germline/.

##Send files to UKCloud
#module load anaconda/3/4.4.0
#source activate UKcloud

#Send sample data to UKCloud
if [[ -d $destination_path ]];
then
	printf "\nTransferring $destination_path to UKCloud...\n"
	#s3cmd put $destination_path --recursive s3://smpaeds/CMP/Panel-Seq/
    $send_data_cmd
	rm -rf $destination_path
	printf "\nTransfer succesful, deleting local copy $destination_path\n"
fi

#Send transfer log data to UKCloud
if [[ -f $transfer_log_file ]];
then
	printf "\nTransferring $transfer_log_file to UKCloud\n"
	#s3cmd put $transfer_log_file s3://smpaeds/CMP/
    $send_log_cmd
fi
