import pygetwindow as gw

with open('C:\\Users\\HP\\.nanobot\\workspace\\open_windows.txt', 'w') as f:
    f.write(str(gw.getAllTitles()))
