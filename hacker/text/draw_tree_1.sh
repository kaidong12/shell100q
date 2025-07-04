
# Creating a Fractal Tree from Y-shaped branches

# This challenge involves the construction of trees, in the form of ASCII Art.

# We have to deal with real world constraints, so we cannot keep repeating the pattern infinitely. 
# So, we will provide you a number of iterations, and you need to generate the ASCII version of the Fractal Tree for only those many iterations (or, levels of recursion). 
# A few samples are provided below.

# Iteration #1
# In the beginning, we simply create a Y. There are 63 rows and 100 columns in the grid below. 
# The triangle is composed of underscores and ones as shown below. 
# The vertical segment and the slanting segments are both 16 characters in length.

# Iteration #2
# At the top of the left and right branches of the first Y, we now add a pair of Y-shapes, 
# which are half the size of the original Y.

# read loop

#!/bin/bash

# Function to draw the fractal tree
draw_tree() {
    local rows=63
    local cols=100
    local iteration=$1
    local max_iteration=5
    
    # Initialize the grid with underscores
    declare -A grid
    for ((i=1; i<=rows; i++)); do
        for ((j=1; j<=cols; j++)); do
            grid[$i,$j]="_"
        done
    done
    
    # Draw the trunk (center column, bottom rows)
    local trunk_length=16
    local center=$((cols/2))
    local start_row=$((rows - trunk_length + 1))
    
    for ((i=start_row; i<=rows; i++)); do
        grid[$i,$center]="1"
    done
    
    # Recursive function to draw branches
    draw_branches() {
        local row=$1
        local col=$2
        local length=$3
        local current_iter=$4
        
        if (( current_iter > iteration )); then
            return
        fi
        
        # Draw left branch
        for ((i=1; i<=length; i++)); do
            local new_row=$((row - i))
            local new_col=$((col - i))
            grid[$new_row,$new_col]="1"
        done
        
        # Draw right branch
        for ((i=1; i<=length; i++)); do
            local new_row=$((row - i))
            local new_col=$((col + i))
            grid[$new_row,$new_col]="1"
        done

        # Recursively draw smaller branches
        local new_length=$((length/2))
        local new_row=$((row - length))
       
        draw_branches $new_row $((col - length)) $new_length $((current_iter + 1))
        draw_branches $new_row $((col + length)) $new_length $((current_iter + 1))
    }
    
    # Start drawing branches from top of trunk
    draw_branches $start_row $center 16 1
    
    # Print the grid
    for ((i=1; i<=rows; i++)); do
        for ((j=1; j<=cols; j++)); do
            printf "%s" "${grid[$i,$j]}"
        done
        printf "\n"
    done
}

# Main script
read -p "Enter number of iterations (1-5): " n
if (( n < 1 || n > 5 )); then
    echo "Please enter a number between 1 and 5"
    exit 1
fi

draw_tree $n

