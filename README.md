# apiknock 

.oO(Knock, Knock... I'm there!)

`apiknock` is a simple tool that helps developers to ensure that no requests can be made
 which are not authorized.
 
## Installation
 
 `apiknock` requires the installation of following packages:
 
 * yaml
 * json
 * requests
 
## Usage

`apiknock` basically works in two phases. First of all a configuration file needs to be created. With this configuration 
file, a configuration can be made (e.g. which users can access which resource). With the finalized configuration file, 
the actual testing phase can be initiated.

### Step 1: Generate configuration file

Use the the `-g` command line switch to generate the configuration file.

```
python apiknock.py -f swagger -g configfile.json path-to-api-file
```

### Step 2: Adjust the configuration
 
Use the included HTML file **knockerconf.html** to adjust the configuration.

### Step 3: Run the knocker

Use the configuration file to run the tests.

```
python apiknock.py -f swagger -c configfile.json -a bearer -1 token1 -2 token2 path-to-api-file
```
### Step 4: JUnit Output

You can add the `-o` parameter to specify an output format and use `-w` to write that output to a file. e.g.

```
python apiknock.py -f swagger -c configfile.json -a bearer -1 token1 -2 token2 -o junit -w junit.xml path-to-api-file
``` 

## Known Limitations

* To reduce the amount of dependencies we removed the usage of prance and build our own OpenAPI-parser. Please let us 
  know, if you find any bugs with this.  
