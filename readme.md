# Python setup Instructions:

This program is designed to run on the python install packaged with ArcGIS Desktop. 

Open a CMD window and enter your python directory. Depending on your install location and ArcGIS version, edit the command below. NOTE: On 64-bit systems, sometimes the correct folder will look like "ArcGISx6410.8". If you have a folder like this, you will most likely need to use it over the "ArcGIS10.8" folder.  

```
cd C:\Python27\Arcgis10.8
```

Install *python-certifi-win32*, using trusted hosts:

```
python -m pip install --trusted-host files.pythonhosted.org  --trusted-host pypi.python.org --trusted-host pypi.org python-certifi-win32
```

Install *pyodbc*. If *python-certifi-win32* installed correctly, the trusted hosts are no longer required:

```
python -m pip install pyodbc
```

You should now be able to run main.py!
