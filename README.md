# README
Hi and welcome to my case for Vandebron. First, I will provide the instructions on how to run this on you system. Then I will provide some reasoning for the choices made
and the next steps needed for this to run in production. If you would first like to read about that, skip to header 'Setup'. 

For this to work, you will need to have docker installed on your laptop.

First, collect your KNMI EDR key and replace the xxx on line 15 in `vandebron/config.py` with your key. 
Sorry, due to time constraints I have not been able to properly implement the environment variables, thus they are still hard-coded in the script.

To set this up, simply run the below command in your terminal in the root of the project.
```shell
make
```

This command will build (or download) all the required docker images:
- The scraper
- Images for the databases
- The image for Dagster

(Apologies for the large image (1,2GB) needed for the timescaledb extension of postgres. Please delete this image afterwards: see below.)

Once everything is set up, navigate to http://localhost:3000/locations/vandebron/asset-groups/default. Then, in the upper right corner click 'Materialize'. 
This will run the created asset (the knmi scraper). This asset collects one day of data from the EDR API, validates and transforms the data and then stores it in the Postgres database.
To see the run, navigate to 'Runs' in the top of the window where you will (hopefully) see a successful run. 

To verify that data has actually been loaded into the database, run the below command. This will fetch 25 rows of data from the database.
```shell
make get-data
```

To view the aggregated data (to 1 hour), call the following command:
```shell
make get-aggregated-data
```

This setup uses the below images. If you like, you can remove these from your system afterwards:
- vandebron-vandebron
- timescale/timescaledb-ha (unless you are using this yourself)
- postgres (unless you are using this yourself)
- vandebron-docker_example_webserver
- vandebron-docker_example_daemon

To remove these images, run:
```shell
docker image rm vandebron-vandebron
```


## Set up
![Diagram](architecture.drawio.png)
#### Scraper
I have created a fairly simple scraper that (for now) collects the 10-minute data for the 17th of February. I have chosen to collect the data from a defined location (De Bilt). 
I can imagine that ideally, we collect data from specific coordinates. For now, I have kept it simple and just collect data from a defined location.
I have added some validation to the data that is collected. Namely, (1) to validate if we receive the same number of values for all parameters as we have timestamps
and (2) to validate if the parameter value types we receive are correct (float) values. For the second part, I created a simple `validate_float` function. This can be expanded to also verify if the actual values fall within a normal range.  
I have decided to not store all the parameters in this demo. I have thought about the use case for the weather data and from the job description and the previous interview, my guess is that this weather data will be used 
to create a forcast of the energy production by the wind turbines. Google told me that wind speed, air pressure and temperature influence the energy production, thus I have only stored parameters related to those three. 
I have created a model for the data and used the built-in Pydantic functionality to also validate the data. If we still pass faulty values to the defined model, Pydantic will raise an error and the job will fail. Then, we will know that we need to improve our validations.  
We can in the future also move/add validations to inside the model. After validation, we transform the data into a desired format (Iterable of dictionary) and store the data in the database.

#### Postgres
I have used Postgres with the timescaledb extension as the database. I believe this extension adds value as the data collected from KNMI is a timeseries. Likely, this KNMI timeseries data will be combined with other timeseries data (e.g. wind turbine data or meter readings).
The timescale extension allows for faster lookup of timeseries data. Plus, we can create a materialized view where we define a time bucket. With this, we can already do some aggregations, therefore potentially helping Data Science. 
In my setup, I have demonstrated this by creating an hourly reading table which contains the averages of all parameter values of that hour. 
I have also created a separate locations table, with a location_id being used in the `knmi_edr_ten_minutes` table. This is to reduce the noise in the 10-minutes data table and allows for additional metadata to be stored in the locations.
When new locations are configured in this scraper job, the python script automatically stores new locations and used them when storing the data.

#### Transformations
A transformation I suggest is what I described in the above paragraph. If I recall correctly, the electricity market works with hourly data. Therefore, I can image we want all data to be on hourly level. 
Thus, I have created a materialized view that displays the data on an hourly level. I have chosen for an average of each hour, but we can discuss with Data Science if this makes sense. Other aggregations are possible on request ofcourse! :)

#### Dagster
A pipeline needs a scheduler ofcourse. We want new data coming in every day, without us having to manually run the script. 
I have had a go at using Dagster as the scheduler in this setup. I have not used this before, but I heard that you guys are using it, so I wanted to try it out. 
I was able to deploy the required images, and we are able to run this pipeline using Dagster. 
There are still quite some limitations to the current setup, but we will discuss them in the next section. 


## Improvements:
Even though there are still a lot of thing to be improved, there is a basis. We are able to collect data, have a basic validation, store the data in a proper format, and we have deployed a scheduler. 
Some next steps will be:
- Actually schedule the job. Right now, we have to manually materialize the run. We could for instance run at 01:00 every day to collect the data for that day. Or run every (few) hour(s) if we need the most up-to-date data. It will depend on when Data Science needs the data and when new KNMI data will become available or updated.
- Make querying for different locations configurable. Say we would like to query for two different locations. Then we should adapt the asset in such a way that we provide the coordinates as a run variable and let the job run twice (once for each location). 
If we wanted to query another location, we simply add more run configurations, and we would not have to touch the code.   
- Improve the use of secrets and environment variables. They are now basically all defined within the script. I am sure Dagster has a nice way for this, I have not had the time to dive into this.
- Logging: I tried to add some descriptive logging statements. However, as per Dagster documentation, it doesn't automatically capture the log from the Python logging module. I tried to add the logger to the dagster.yaml, but I was not able to capture it.
Therefore, this is also up for improvements.
- Add more validation on the data coming in, therefore making it more robust than it is at the moment.