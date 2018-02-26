-- script to populate the esgf_security database with the required data

-- groups
insert into esgf_security.group (id, name, description, visible, automatic_approval) values (1, 'wheel', 'Administrator Group', true, true);

-- roles
insert into esgf_security.role (id, name, description) values (1, 'super', 'Super User');
insert into esgf_security.role (id, name, description) values (2, 'user', 'Standard User');
insert into esgf_security.role (id, name, description) values (3, 'admin', 'Group Administrator');
insert into esgf_security.role (id, name, description) values (4, 'publisher', 'Data Publisher');
insert into esgf_security.role (id, name, description) values (5, 'test', 'Test Role');
insert into esgf_security.role (id, name, description) values (6, 'none', 'None');

