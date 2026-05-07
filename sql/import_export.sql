-- Import examples (adjust path to your own CSV location)
LOAD DATA INFILE '/path/to/member.csv'
INTO TABLE member
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(member_id, genealogy_id, name, gender, birth_year, death_year, biography);

LOAD DATA INFILE '/path/to/parent_child.csv'
INTO TABLE parent_child
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(parent_id, child_id, relation_type);

LOAD DATA INFILE '/path/to/marriage.csv'
INTO TABLE marriage
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(marriage_id, spouse1_id, spouse2_id, start_date, end_date, status);

-- Export examples
SELECT *
INTO OUTFILE '/path/to/out_member.csv'
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM member;

SELECT *
INTO OUTFILE '/path/to/out_parent_child.csv'
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM parent_child;

SELECT *
INTO OUTFILE '/path/to/out_marriage.csv'
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM marriage;
