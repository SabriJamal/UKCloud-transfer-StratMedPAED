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
data_report_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/001.reports"
data_analysis_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/3.analysis"
#data_fastq_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/2.fastq"
data_fastq_path="/data/rds/DMP/DUDMP/TRANSGEN/TIER2/transgen-mdx/003.Fastqs"
destination_path="/scratch/DMP/DUDMP/TRANSGEN/transgen-mdx/ngs/UKCloud"
transfer_log_file="samples_ready_to_transfer.log"
transfer_log_file="$destination_path/$transfer_log_file"
sample_name=$sample_t
uk_cloud_desination="s3://smpaeds/CMP/lcWGS_auto/lcWGS-Relapse/"
uk_cloud_log_file_desintation="s3://smpaeds/CMP/"

#Compounded vars
full_sample_name=$(ls $data_fastq_path/$pool/$sample_name*R1* | rev | cut -d"/" -f1 | rev | cut -d"_" -f1)

if ls $data_fastq_path/$pool/$sample_name*R1* 1> /dev/null 2>&1;
then
    echo "Fastq file exists, proceeeding with transfer"
else
    echo "Fastq file does not exist EXITING TRANSFER, RESOLVE"
    echo "See file for full details of all samples missing fastq data => $destination_path/fastq_missing.transfer_terminated.txt"
    printf "$pool\t$trial_id\t$sample_t\t$sample_b\n" >> $destination_path/fastq_missing.transfer_terminated.txt
    echo "Exiting..."
    exit 1
fi

destination_path="$destination_path/$full_sample_name"

##Create destination folder
mkdir $destination_path

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
cp -r $data_analysis_path/$pool/CNVs/*$trial_id*/* $destination_path/CNVs/.

#SVs (Remove intermediary SV files)
#mkdir -p $destination_path/SVs/Manta
#cp -r $data_analysis_path/$pool/SVs/AnnotSV/*$trial_id*-T/* $destination_path/SVs/Manta/.
#rm $destination_path/SVs/Manta/*[wW]orkflow*
#rm -rf $destination_path/SVs/Manta/workspace

#Stats
mkdir $destination_path/Stats
cp $data_report_path/$pool/Stats/*$trial_id* $destination_path/Stats/.

#Variants (Raw VCF)
#mkdir -p $destination_path/Variants/Germline
#mkdir -p $destination_path/Variants/Somatic
#cp $data_report_path/$pool/Variants/$sample_b-$trial_id-B/SNV.$sample_t-$trial_id-T.vcf $destination_path/Variants/Somatic/.
#cp $data_report_path/$pool_germ/Variants/$sample_b-$trial_id-B/GATK*$trial_id-B.vcf $destination_path/Variants/Germline/.

##Send files to UKCloud
module load anaconda/3/4.4.0
source activate UKcloud

#Send sample data to UKCloud
if [[ -d $destination_path ]];
then
	printf "\nTransferring $destination_path to UKCloud...\n"
	s3cmd put $destination_path --recursive $uk_cloud_desination
	rm -rf $destination_path
	printf "\nTransfer succesful, deleting local copy $destination_path\n"
fi

#Send transfer log data to UKCloud
if [[ -f $transfer_log_file ]];
then
	printf "\nTransferring $transfer_log_file to UKCloud\n"
	s3cmd put $transfer_log_file $uk_cloud_log_file_desintation
fi
