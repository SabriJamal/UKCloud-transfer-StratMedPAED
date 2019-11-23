# UKCloud-transfer-StratMedPAED
This repository contains the scripts necessary for the automated UKCloud transfer (sharing of NGS data for the StratMed PAED project). The NGS data is generated through the Molecular Diagnostics Information Management System a web application hosting an NGS pipeline for SNV, CNV and SV calling, developed by the bioinformatics team at the Centre of Molecular Pathology in Sutton, UK.

## Usage & Installation
It does not require any installation other than cloning this repository and configuring the YAML config file (see configurations in usage)

## Configurations
The YAML config file is used to configure configurations neccessary. Such high level configurations is the:
* Sample sheet structure and extension storing sample data
* Target panel to fetch data from
* Name of logfile to output a record for each sample
* File system related configrations such as paths etc.

## Logs
All actions taken, such as scanning for completion of blind analysis, UKCloud transfer etc. All are logged with a time stamp and written to standard out. 

## Workflow 
The workflow architecture can be found in workflow_diagram folder both as a .png and .graphml (for usage with yED).

## Credits
Author: Sabri Jamal
