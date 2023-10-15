#!/bin/sed -f
#all comment lines must start with a hash '#'
#name:sed.sh
#to call: ./sed.sh testcase.log


#2p

#1,3p

#/^d/p


#print the content between 20 to /sys/
#20,/sys/p
#1,$p


#only display the line number
#20,/sys/=


####################################
#20p
#/sys/=
#/.*conf/p


#append text
#/sys/ a\ \nhello, there is a system parameter emerged!!!!!!!!!!!\n

#insert text before current line
#/sys/ i\ \nhaha, there is a system parameter emerging!!!!!!!!!!!!\n


#modify the context
#/sys/ c\ hoho, the original text has been changed!!!!!!!!!!!



#replace text
#s/root/lance/g


#output to another file
#s/root/lance/w sed.out


#use & to record the fileds
#s/root/haha, i'm &\t/g


#read text from another file and append to the next few lines
#/sys/r cpucase.log


#match and quit
#/sys/q


#display the control character #l
1,$l

