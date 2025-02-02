![SUMO logo](https://github.com/ophie200/sumo/blob/master/images/SUMO-logo.png)

# SUMO Data Access

Scripts to pull data from various sources for SUMO Dashboards and upload it to GCP.  

## Datasource Overview

### Google Analytics
Uses Google Analytics Reporting API v4 to pull dimensions and metrics for the Google Analytics SUMO report.

https://developers.google.com/analytics/devguides/reporting/core/v4/rest/

Make sure Analytics Reporting API is enabled in the GCP running the code.
A valid service account should be permissioned to pull data from the SUMO report from the Google Analytics side.
GoogleAnalytics/create_ga_tables.py creates Google Analytics BiqQuery tables with schema definition.
GoogleAnalytics/get_ga_data.py pulls data for a given range. The data is written to local csv files in /tmp folder, and pushed to google storage gs://<sumo-bucket>/googleanalytics/. The google storage files are uploaded to BigQuery dataset sumo table ga_*. After upload, the files are moved to the /processed subfolder.  Some of the data pulls hit daily data limits so it is recommend to run data pulls in one month chunks. 


## Installing / Getting started

The scripts are intended to be run on a Google Cloud Project with necessary account permissions. 

Assumes Google storage folder structure:
```shell
gs:// <sumo-bucket>  
    / googleanalytics => where google analytics data files are initially placed
    / googleanalytics / processed => where processed google analytics data files are placed after being uploaded to BigQuery
    / googleplaystore => where google  data files are initially placed [deprecated]
    / googleplaystore / processed => where processed google analytics data files are placed after being uploaded to BigQuery [deprecated]
    / tmp => model param files, aggregation files in subfolder by model pararm
gs:// <data-bucket> => location of parquet input data files
```

```shell
packagemanager install awesome-project
awesome-project start
awesome-project "Do something!"  # prints "Nah."
```

Here you should say what actually happens when you execute the code above.

### Initial Configuration

Some projects require initial configuration (e.g. access tokens or keys, `npm i`).
This is the section where you would document those requirements.

## Developing

Here's a brief intro about what a developer must do in order to start developing
the project further:

```shell
git clone https://github.com/your/awesome-project.git
cd awesome-project/
packagemanager install
```

And state what happens step-by-step.

### Building

If your project needs some additional steps for the developer to build the
project after some code changes, state them here:

```shell
./configure
make
make install
```

### Units Tests

```shell
python setup.py test
```
Sigh, maybe someday.

### Deploying / Publishing

Define GCP storage bucket where files should go.

```shell
packagemanager deploy awesome-project -s server.com -u username -p password
```

And again you'd need to tell what the previous code actually does.

## Features

What's all the bells and whistles this project can perform?
* What's the main functionality
* You can also do another thing
* If you get really randy, you can even do this

## Configuration

Here you should write what are all of the configurations a user can enter when
using the project.

#### Argument 1
Type: `String`  
Default: `'default value'`

State what an argument does and how you can use it. If needed, you can provide
an example below.

Example:
```bash
awesome-project "Some other value"  # Prints "You're nailing this readme!"
```

#### Argument 2
Type: `Number|Boolean`  
Default: 100

Copy-paste as many of these as you need.

## Contributing

When you publish something open source, one of the greatest motivations is that
anyone can just jump in and start contributing to your project.

These paragraphs are meant to welcome those kind souls to feel that they are
needed. You should state something like:

"If you'd like to contribute, please fork the repository and use a feature
branch. Pull requests are warmly welcome."

If there's anything else the developer needs to know (e.g. the code style
guide), you should link it here. If there's a lot of things to take into
consideration, it is common to separate this section to its own file called
`CONTRIBUTING.md` (or similar). If so, you should say that it exists here.

## Links

Even though this information can be found inside the project on machine-readable
format like in a .json file, it's good to include a summary of most useful
links to humans using your project. You can include links like:

- Project homepage: https://your.github.com/awesome-project/
- Repository: https://github.com/your/awesome-project/
- Issue tracker: https://github.com/your/awesome-project/issues
  - In case of sensitive bugs like security vulnerabilities, please contact
    my@email.com directly instead of using issue tracker. We value your effort
    to improve the security and privacy of this project!
- Related projects:
  - Your other project: https://github.com/your/other-project/
  - Someone else's project: https://github.com/someones/awesome-project/


## Licensing
Licensed under ... For details, see the LICENSE file.
