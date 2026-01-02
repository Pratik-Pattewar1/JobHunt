## Author
- Name: Pratik Pattewar
- Role: fullstack developer
- Contact: pratikpattewar1@gmail.com
## MYSQL Database 

1. Create a Database schema named :  user-system

2. Create a 'user' table with column userid , name , email, password   

3. Create a 'job' table by id, userid , email, qualification , skills , jobs by command :-
      
    CREATE TABLE job (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_title VARCHAR(255) NOT NULL,
        job_role VARCHAR(255) NOT NULL,
        skills VARCHAR(255) NOT NULL,
        qualifications TEXT NOT NULL,
        vacancy INT NOT NULL,
        last_date DATE NOT NULL
     );

4. create a 'applied_job' table by following command :

      CREATE TABLE applied_job (
    	   id INT AUTO_INCREMENT PRIMARY KEY,
    	   email VARCHAR(255) NOT NULL,
    	   job_title VARCHAR(255) NOT NULL,
    	   job_role VARCHAR(255) NOT NULL,
    	   skills TEXT NOT NULL
       );
