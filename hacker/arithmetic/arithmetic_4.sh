#Given two integers, X and Y , find their sum, difference, product, and quotient.

# Input Format

# Two lines containing one integer each (X and Y, respectively).

# Constraints
# -100<= X,Y <= 100
# Y!=0

# Output Format

# Four lines containing the sum (x+y), difference (x-y), product (XxY), and quotient (X/Y), respectively.
# (While computing the quotient, print only the integer part.)

#!/bin/bash

read a
read b

echo $((a+b))
echo $((a-b))
echo $((a*b))
echo $((a/b))


