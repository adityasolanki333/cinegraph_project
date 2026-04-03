
import os

def count_lines(filename):
    f = open(filename, 'rb')
    lines = 0
    buf_size = 1024 * 1024
    read_f = f.read # loop optimization

    buf = read_f(buf_size)
    while buf:
        lines += buf.count(b'\n')
        buf = read_f(buf_size)
    
    return lines

path = r"C:\Users\solan\Desktop\Cinema-Guide\Cinema-Guide\datasets\TMDB_all_movies.csv"
try:
    count = count_lines(path)
    print(f"Total Movies: {count - 1}") # Minus header
except Exception as e:
    print(f"Error: {e}")
