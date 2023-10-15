#!/bin/awk -f
#all commentt lines must start with a hash '#'
#name:awk.sh
#to call: awk.sh testcase.log
#prints total and average of club student points

#print a header first
BEGIN{
#FS=":"
OFS="###"
ORS="\n"
#print "Student name"

print "========================================="
}

#let's print the information
{

#print $0
#if ($1 ~ /^-/) tot+=$5
#if ($1 ~ /^d/) tot+=$5


#format the print lines
#"============================================="
#printf("%12s%20s\n",$1,$7)
#printf("%-12s%-20s\n",$1,$7)
#printf("%12shahas%20s\thoho\n",$1,$7)


#pass parameter from command line
#"============================================="
#if(NF<MAX) print "the lines do not have so many fileds!";


#Array
split($0,myarray,":")
  for(fi in myarray){
  #print fi
  print myarray[fi]

  }

}

#finished processing, now let's print the total and average point
END{
print "========================================="
print "File Name :" FILENAME
print "Total row :" NR
#print "Club student total points :" tot
#print "Average Club Student point :" tot/NR
}

