#Given three integers (X, Y, and Z) representing the three sides of a triangle, 
#identify whether the triangle is scalene, isosceles, or equilateral.

# If all three sides are equal, output EQUILATERAL.
# Otherwise, if any two sides are equal, output ISOSCELES.
# Otherwise, output SCALENE.

# Input Format
# Three integers, each on a new line.

# Constraints
# 1<=x,y,z<=1000
# The sum of any two sides will be greater than the third.

# Output Format
# One word: either "SCALENE" or "EQUILATERAL" or "ISOSCELES" (quotation marks excluded).

#!/bin/bash

read sa
read sb
read sc

if [ $sa -eq $sb -a $sa -eq $sc -a $sb = $sc ];then
    echo "EQUILATERAL"
elif [ $sa -eq $sb -o $sa -eq $sc -o $sb = $sc ];then
    echo "ISOSCELES"
else
    echo "SCALENE"
fi

