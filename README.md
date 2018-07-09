# Item Catalog Project
Udacity Full Stack Web Developer Nano Degree Project #4

This is a simple, responsive CRUD web application to track personal spendings with an individualized user experience

The code adopted some starter code from Udacity's Full Stack Nano Degree Course on CRUD functionalities.

## Install
To start on this project, you'll need database software (provided by a Linux virtual machine) and the data to analyze.

My project used the following,
* Python 2
* VirtualBox(An alternative virtual machine can be used) 
* Vagrant (To manage the VM and use the pre-provided installations by Udacity )

1. Install Vagrant and VirtualBox
2. Clone the fullstack-nanodegree-vm 
3. Download/Clone this directory and move it in the Vagrant directory.
4. Run your application within the VM (python /vagrant/catalog/application.py)
5. Access application by visiting http://localhost:8000 locally


## Usage

After going through the installation, run the following command from a command line. 
```
$ python application.py
```

Access the application through your preferred web browser. 

### Login

You can login using your Google Account through the login page

### Add Spendings

On the navigation on the top of the website, there is a link to add your spendings.

### JSON

The JSON API is accessible through the link on the top right of the naviation. You will only be able to reach your specific spendings. 
	
#### API Usage
GET /spending/

| Name     | Data Type | Description        |
|----------|-----------|--------------------|
| name     | string    | Name of Spending   |
| id       | int       | ID (Primary Key)   |
| merchant | string    | Vendor             |
| price    | string    | Amount of Spending |


## Future Updates 
* Create balance of budget
* Photo feature available after login 
* Options to add date of expenditure 
* Sort the spendings

## Issues
* Feel free to reach out to me if there are any issues with the application. 
