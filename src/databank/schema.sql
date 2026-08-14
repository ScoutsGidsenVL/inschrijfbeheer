create table categorie (
	id varchar primary key,
	naam varchar unique not null, /* Zou uniek moeten zijn */
	alt_naam varchar
);

create table evenement_status (
	id serial primary key,
	beschrijving varchar not null
);

insert into evenement_status values (1, 'Actief'), (2, 'Geannuleerd');

create table locatie (
	id serial primary key,
	naam varchar,
	straat varchar,
	huisnummer varchar,
	postcode varchar, /* TODO: bepalen waar omzetting int-string gebeurt */
	stad varchar,
	
	constraint naam_of_adres check (
		(naam is not null) 
		or (
			(straat is not null) 
			and (huisnummer is not null) 
			and (postcode is not null) 
			and (stad is not null)
		)
	)
);

create table evenement (
	id varchar primary key,
	titel varchar not null,
	status int default 1,
	beschrijving varchar,
	locatie int not null,
	
	starttijd timestamp not null,
	eindtijd timestamp not null,
	
	min_deelnemers int, 
	max_deelnemers int,

	aantal_zelfde_groep int,
	
	min_leeftijd int,

	categorie varchar,
	constraint positief_min check (min_deelnemers >= 0),
	constraint positief_max check (max_deelnemers >= 0 and max_deelnemers >= min_deelnemers),
	constraint positief_aantal check (aantal_zelfde_groep >= 0 or aantal_zelfde_groep is null),
	constraint positief_min_leeftijd check (min_leeftijd >= 0 or min_leeftijd is null),
	constraint einde_na_start check (eindtijd  > starttijd),

	constraint fk_evenement_status foreign key (status) references evenement_status (id) on delete set null,
	constraint fk_evenement_categorie foreign key (categorie) references categorie (id) on delete set null,
	constraint fk_evenement_locatie foreign key (locatie) references locatie (id) on delete restrict
);

create table deelnemertype (
	id varchar primary key,
	evenement varchar not null,
	naam varchar, /* Potentieel constraint met ID dat combo uniek is */
	prijs int,
	constraint positieve_prijs check (prijs >= 0),
	quota int,
	constraint positief_quota check (quota >= 0 or quota is null), /* Is dit limiet of doel? */
	starttijd_inschrijving timestamp not null,
	eindtijd_inschrijving timestamp not null,

	constraint einde_na_start check (eindtijd_inschrijving  > starttijd_inschrijving),
	
	constraint fk_deelnemertype_evenement foreign key (evenement) references evenement (id) on delete cascade
	
);

create table inschrijving (
	evenement varchar not null,
	deelnemertype varchar not null,
	lid varchar not null, /* id van lid - mag aangenomen worden dat dit altijd hex is? */
	tijdstip timestamp default NOW(),
	is_betaald bool default true,
	is_geannuleerd bool default false,
	is_terugbetaald bool default false,
	/* TODO: maak eigen tabel voor bron van datas
	_is_weez bool default true,
	_laatste_sync timestamp default NOW(),
	*/
	
	primary key (evenement, lid), /* Staat 1 inschrijving per lid toe? */
	
	constraint fk_inschrijving_evenement foreign key (evenement) references evenement (id) on delete restrict,
	constraint fk_inschrijving_tarief foreign key (deelnemertype) references deelnemertype (id) on delete restrict

	/*
	gouw varchar not null,
	district varchar not null,
	groep varchar not null,
	module_naam varchar not null,
	module_nummer varchar not null
	
	*/
);