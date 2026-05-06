@echo off
REM Run this file inside an Anaconda Prompt.
conda create -n gene-tree python=3.11 -y
call conda activate gene-tree
pip install -r requirementlist.txt
echo Environment ready: gene-tree
