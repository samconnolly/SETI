drop table if exists entries;

create table config(
	id integer primary key autoincrement,
	active integer not null,
	released integer not null,
    reg integer not null
);
