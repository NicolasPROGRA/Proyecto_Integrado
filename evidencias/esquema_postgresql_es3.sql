-- Esquema PostgreSQL ES3 / Salud Municipal Padre Las Casas

-- Generado desde app/models.py. Crear antes una base vacía con pgAdmin.

-- La aplicación también puede crear el esquema mediante SQLAlchemy.

CREATE TABLE canal (
	id SERIAL NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE categoria (
	id SERIAL NOT NULL, 
	name VARCHAR(70) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE ciudadano (
	id SERIAL NOT NULL, 
	alias VARCHAR(100), 
	email VARCHAR(255), 
	contact_consent BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE estado_caso (
	id SERIAL NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE pregunta_encuesta (
	id SERIAL NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	text VARCHAR(240) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE rol (
	id SERIAL NOT NULL, 
	code VARCHAR(30) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE tipo_registro (
	id SERIAL NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE unidad (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE registro (
	id SERIAL NOT NULL, 
	folio VARCHAR(40) NOT NULL, 
	tracking_hmac VARCHAR(64) NOT NULL, 
	record_type_id INTEGER NOT NULL, 
	channel_id INTEGER NOT NULL, 
	category_id INTEGER, 
	status_id INTEGER, 
	citizen_id INTEGER, 
	unit_id INTEGER, 
	facility VARCHAR(100) NOT NULL, 
	source_area VARCHAR(100) NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT tracking_hmac_length CHECK (length(tracking_hmac) = 64), 
	FOREIGN KEY(record_type_id) REFERENCES tipo_registro (id) ON DELETE RESTRICT, 
	FOREIGN KEY(channel_id) REFERENCES canal (id) ON DELETE RESTRICT, 
	FOREIGN KEY(category_id) REFERENCES categoria (id) ON DELETE RESTRICT, 
	FOREIGN KEY(status_id) REFERENCES estado_caso (id) ON DELETE RESTRICT, 
	FOREIGN KEY(citizen_id) REFERENCES ciudadano (id) ON DELETE SET NULL, 
	FOREIGN KEY(unit_id) REFERENCES unidad (id) ON DELETE RESTRICT
);

CREATE TABLE usuario_admin (
	id SERIAL NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role_id INTEGER NOT NULL, 
	unit_id INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	FOREIGN KEY(role_id) REFERENCES rol (id) ON DELETE RESTRICT, 
	FOREIGN KEY(unit_id) REFERENCES unidad (id) ON DELETE RESTRICT
);

CREATE TABLE adjunto (
	id SERIAL NOT NULL, 
	record_id INTEGER NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(255) NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT attachment_nonnegative_size CHECK (size_bytes >= 0), 
	FOREIGN KEY(record_id) REFERENCES registro (id) ON DELETE CASCADE, 
	UNIQUE (storage_key)
);

CREATE TABLE auditoria (
	id SERIAL NOT NULL, 
	actor_id INTEGER, 
	record_id INTEGER, 
	event_type VARCHAR(70) NOT NULL, 
	details JSONB NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES usuario_admin (id) ON DELETE SET NULL, 
	FOREIGN KEY(record_id) REFERENCES registro (id) ON DELETE SET NULL
);

CREATE TABLE respuesta_encuesta (
	id SERIAL NOT NULL, 
	record_id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT survey_rating_range CHECK (rating BETWEEN 1 AND 5), 
	CONSTRAINT uq_respuesta_registro_pregunta UNIQUE (record_id, question_id), 
	FOREIGN KEY(record_id) REFERENCES registro (id) ON DELETE CASCADE, 
	FOREIGN KEY(question_id) REFERENCES pregunta_encuesta (id) ON DELETE RESTRICT
);

CREATE TABLE seguimiento (
	id SERIAL NOT NULL, 
	case_id INTEGER NOT NULL, 
	actor_id INTEGER, 
	status_id INTEGER, 
	target_unit_id INTEGER, 
	action VARCHAR(180) NOT NULL, 
	note VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES registro (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_id) REFERENCES usuario_admin (id) ON DELETE SET NULL, 
	FOREIGN KEY(status_id) REFERENCES estado_caso (id) ON DELETE RESTRICT, 
	FOREIGN KEY(target_unit_id) REFERENCES unidad (id) ON DELETE RESTRICT
);

CREATE INDEX ix_registro_unidad_estado_fecha ON registro (unit_id, status_id, created_at);

CREATE INDEX ix_registro_tipo_categoria_fecha ON registro (record_type_id, category_id, created_at);

CREATE UNIQUE INDEX ix_registro_folio ON registro (folio);

CREATE INDEX ix_auditoria_evento_fecha ON auditoria (event_type, created_at);

CREATE INDEX ix_respuesta_pregunta_fecha ON respuesta_encuesta (question_id, created_at);

CREATE INDEX ix_seguimiento_case_id ON seguimiento (case_id);
