create table categorie (
	id varchar primary key,
	naam varchar unique not null, /* Zou uniek moeten zijn */
	alt_naam varchar,
	
	_is_weez bool default true,
	_laatste_sync timestamp default NOW()
	
);

create table tarief (
	id varchar primary key
	naam varchar, /* Potentieel constraint met ID dat combo uniek is */
	prijs int constraint positieve_prijs check (prijs >= 0),
	quota int constraint positief_quota check (quota >= 0), /* Is dit limiet of doel? */
	starttijd_inschrijving timestamp default NOW(),
	eindtijd_inschrijving timestamp default starttijd,
	_is_weez bool default true,
	_laatste_sync timestamp default NOW()

	constraint einde_na_start check (eindtijd_inschrijving  > starttijd_inschrijving)
	
); /* Meerdere tarieven worden gebruikt oa voor bepalen van een activiteit */

create table evenement (
	id varchar primary key,
	titel varchar not null,
	beschrijving varchar,
	starttijd timestamp not null,
	eindtijd timestamp not null,
	locatie varchar, /* Naam van de locatie */
	straat varchar,
	huisnummer varchar,
	postcode varchar, /* Voorlopig geen zin in conversies */
	stad varchar,
	min_deelnemers int constraint positief_min check (min_deelnemers >= 0),
	max_deelnemers int constraint positief_max check (max_deelnemers >= 0 and max_deelnemers >= min_deelnemers),
	_is_weez bool default true,
	_laatste_sync timestamp default NOW(),
	
	categorie varchar references categorie(id),
	
	constraint einde_na_start check (eindtijd  > starttijd)
	constraint adres_of_locatie check (locatie or (straat and huisnummer and postcode and stad)) /* Ofwel is er een adres of een locatie */
);

create table inschrijving (
	evenement int references evenement(id) not null,
	tarief varchar references tarief(id) not null,
	lid varchar not null, /* id van lid - mag aangenomen worden dat dit altijd hex is? */
	tijdstip timestamp default NOW(),
	is_betaald bool default true,
	is_geannuleerd bool default false,
	is_terugbetaald bool default false,
	opmerking varchar,
	_is_weez bool default true,
	_laatste_sync timestamp default NOW(),
	
	primary key (evenement, lid) /* Staat 1 inschrijving per lid toe? */
);

create table evenement_tarief (
	evenement int references evenement(id) not null,
	tarief varchar references tarief(id) not null,
	_is_weez bool default true,
	_laatste_sync timestamp default NOW(),
	
	primary key (evenement, tarief)
);

