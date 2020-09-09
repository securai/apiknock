# apiknock 

.oO(Knock, Knock... I'm there!)

`apiknock` is a simple tool that helps developers ensure that no requests can be made
 which are not authorized.
 
## Installation
 
 `apiknock` requires the installation of following packages:
 
 * prance 
 * openapi-spec-validator
 * requests
 
## Usage

`apiknock` basically works in two phases. First of all a configuration file needs to be created. With this configuration 
file, a configuration can be made (e.g. which users can access which resource). With the finalized configuration file, 
the actual testing phase can be initiated.

### Step 1: Generate configuration file

Use the the `-g` command line switch to generate the configuration file.

```
python3 apiknock -f swagger -g configfile.json path-to-api-file
```

### Step 2: Adjust the configuration
 
Use the included HTML file **knockerconf.html** to adjust the configuration.

### Step 3: Run the knocker

Use the configuration file to run the tests.

```
python3 apiknock -f swagger -c configfile.json -a bearer -1 token1 -2 token2 path-to-api-file
```

## Known Limitations

* Currently only Swagger (OpenAPI-2) ist supported. OpenAPI 3 is WIP
* Only a maximum of three different users are supported at the moment, as apiknock is still in PoC-phase
