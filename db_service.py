import os
import datetime
import sqlalchemy
from flask import Flask, render_template, request, url_for, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import func
from werkzeug.utils import secure_filename


basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join('staticFiles', 'images')

app = Flask(__name__, template_folder='templates', static_folder='staticFiles')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sqlite_darts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Secret key'

db = SQLAlchemy(app)


def model_to_json(obj):
    return {k: v for k, v in obj.__dict__.items() if k != "_sa_instance_state"}


class LongRead(db.Model):
    __tablename__ = 'LongRead'
    id = db.Column(db.Integer, primary_key=True)
    world_id = db.Column(db.Integer, db.ForeignKey('World.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    img_link = db.Column(db.String(200), nullable=True)

    # timeline attributes
    map_link = db.Column(db.String(200), nullable=True)
    timeline_link = db.Column(db.String(200), nullable=True)

    chapters = db.relationship('Chapter', backref='longread', lazy=True)
    blockcontents = db.relationship('BlockContent', backref='longread', lazy=True)

    def __repr__(self):
        return f'<LongRead {self.name}>'


class Chapter(db.Model):
    __tablename__ = 'Chapter'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    longread_id = db.Column(db.Integer, db.ForeignKey('LongRead.id'), nullable=False)

    blockcontents = db.relationship('BlockContent', backref='chapter', lazy=True)

    def __repr__(self):
        return f'<Chapter {self.name}>'


class BlockContent(db.Model):
    __tablename__ = 'BlockContent'
    id = db.Column(db.Integer, primary_key=True)
    longread_id = db.Column(db.Integer, db.ForeignKey('LongRead.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('Chapter.id'), nullable=False)
    text = db.Column(db.String(10000), nullable=True)
    img_link = db.Column(db.String(200), nullable=True)

    # event attributes
    coordx = db.Column(db.Integer, nullable=True)
    coordy = db.Column(db.Integer, nullable=True)
    time = db.Column(db.Integer, nullable=True)
    floating_text = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<BlockContent {self.id}>'


class World(db.Model):
    __tablename__ = 'World'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    img_link = db.Column(db.String(200), nullable=True)
    description = db.Column(db.String(10000), nullable=False)

    longreads = db.relationship('LongRead', backref='world', lazy=True)
    worldobjs = db.relationship('WorldObj', backref='world', lazy=True)

    def __repr__(self):
        return f'<World {self.name}>'


blockcontents = db.Table('blockcontents',
                         db.Column('blockcontent_id', db.Integer, db.ForeignKey('BlockContent.id'), primary_key=True),
                         db.Column('worldobj_id', db.Integer, db.ForeignKey('WorldObj.id'), primary_key=True)
                         )


class WorldObj(db.Model):
    __tablename__ = 'WorldObj'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    world_id = db.Column(db.Integer, db.ForeignKey('World.id'), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    img_link = db.Column(db.String(200), nullable=True)

    blockcontents = db.relationship('BlockContent',
                                    secondary=blockcontents,
                                    lazy='subquery',
                                    backref=db.backref('worldobj', lazy=True))

    def __repr__(self):
        return f'<WorldObj {self.name}>'


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longread/chapter/blockcontent/all", methods=["POST"])
def blockcontents_chapter_getAll():
    try:
        chapter_id = request.json["chapter_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    chapter = Chapter.query.get_or_404(chapter_id)
    blockcontents = [model_to_json(bc) for bc in chapter.blockcontents]
    return jsonify(blockcontents)


@app.route("/longread/chapter/blockcontent", methods=["POST"])
def blockcontent():
    try:
        blockcontent_id = request.json["blockcontent_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    return jsonify(model_to_json(blockcontent))


@app.route("/longread/chapter/blockcontent/create", methods=["POST"])
def blockcontent_create():
    try:
        longread_id = request.json["longread_id"]
        chapter_id = request.json["chapter_id"]
        text = request.json["text"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    coordx = -1
    coordy = -1
    time = datetime.datetime.now()
    floating_text = ""

    blockcontent = BlockContent(longread_id=longread_id,
                                chapter_id=chapter_id,
                                text=text,
                                img_link = "/staticFiles/images/font.jpg")

    db.session.add(blockcontent)
    db.session.commit()

    return jsonify({"message": "BlockContent create successfully."}), 201


@app.route("/longread/chapter/blockcontent/edit", methods=["POST"])
def blockcontent_edit():
    try:
        blockcontent_id = request.json["blockcontent_id"]
        text = request.json["text"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400
    
    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    blockcontent.text = text

    db.session.add(blockcontent)
    db.session.commit()

    return jsonify({"message": "BlockContent edit successfully."}), 200


@app.route("/longread/chapter/blockcontent/delete", methods=["POST"])
def blockcontent_delete():
    try:
        blockcontent_id = request.json["blockcontent_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400
    
    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    if blockcontent.img_link != "/staticFiles/images/font.jpg":
        os.remove(blockcontent.img_link[1:])

    db.session.delete(blockcontent)
    db.session.commit()

    return jsonify({"message": "BlockContent delete successfully."}), 200


@app.route("/longread/chapter/blockcontent/<int:blockcontent_id>/edit_image", methods=["POST"])
def edit_blockcontent_image(blockcontent_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    blockcontent = BlockContent.query.get_or_404(blockcontent_id)

    filename = uploaded_img.filename
    if filename != "":
        if blockcontent.img_link != "/staticFiles/images/font.jpg":
            os.remove(blockcontent.img_link[1:])
        blockcontent_img_name = "blockcontent" + str(blockcontent.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], blockcontent_img_name))
        blockcontent.img_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], blockcontent_img_name)

        db.session.add(blockcontent)
        db.session.commit()

    return jsonify({"message": "BlockContent image edit successfully"}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longread/chapter/all", methods=["POST"])
def chapters_getAll():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    chapters = [model_to_json(ch) for ch in longread.chapters]
    return jsonify(chapters)


@app.route("/longread/chapter", methods=["POST"])
def chapter():
    try:
        chapter_id = request.json["chapter_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    chapter = Chapter.query.get_or_404(chapter_id)
    return jsonify(model_to_json(chapter))


@app.route("/longread/chapter/create", methods=["POST"])
def chapters_create():
    try:
        longread_id = request.json["longread_id"]
        name = request.json["name"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    chapter = Chapter(name=name, longread_id=longread_id)

    db.session.add(chapter)
    db.session.commit()

    return jsonify({"message": "Chapter create successfully."}), 201


@app.route("/longread/chapter/edit", methods=["POST"])
def chapters_edit():
    try:
        chapter_id = request.json["chapter_id"]
        name = request.json["name"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    chapter = Chapter.query.get_or_404(chapter_id)
    chapter.name = name

    db.session.add(chapter)
    db.session.commit()

    return jsonify({"message": "Chapter edit successfully."}), 200


@app.route("/longread/chapter/delete", methods=["POST"])
def chapter_delete():
    try:
        chapter_id = request.json["chapter_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    chapter = Chapter.query.get_or_404(chapter_id)
    for blockcontent in chapter.blockcontents:
        blockcontent_delete(blockcontent.id)

    db.session.delete(chapter)
    db.session.commit()

    return jsonify({"message": "Chapter delete successfully."}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longreads/all", methods=["POST"])
def longreads():
    longreads = LongRead.query.all()
    longreads_json = [model_to_json(lr) for lr in longreads]
    return jsonify(longreads_json)


@app.route("/world/longread/all", methods=["POST"])
def longreads_getAll():
    try:
        world_id = request.json["world_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    world = World.query.get_or_404(world_id)
    longreads = [model_to_json(lr) for lr in world.longreads]
    return jsonify(longreads)


@app.route("/world/longread", methods=["POST"]) 
def longread():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    return jsonify(model_to_json(longread))


@app.route("/world/longread/create", methods=["POST"])
def longread_create():
    try:
        world_id = request.json["world_id"]
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead(world_id=world_id,
                        name=name,
                        description=description,
                        img_link="/staticFiles/images/QuestionMark.jpg",
                        timeline_link="/staticFiles/images/timeline_base.jpg",
                        map_link="/staticFiles/images/map_base.jpg")

    db.session.add(longread)
    db.session.commit()

    return jsonify({"message": "Longread create successfully."}), 201


@app.route("/world/longread/edit", methods=["POST"])
def longread_edit():
    try:
        longread_id = request.json["longread_id"]
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    longread.name = name
    longread.description = description

    db.session.add(longread)
    db.session.commit()

    return jsonify({"message": "Longread edit successfully."}), 200


@app.route("/world/longread/delete", methods=["POST"])
def longread_delete():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    for chapter in longread.chapters:
        chapter_delete(chapter.id)
    if longread.img_link != "/staticFiles/images/QuestionMark.jpg":
        os.remove(longread.img_link[1:])

    db.session.delete(longread)
    db.session.commit()

    return jsonify({"message": "Longread delete successfully."}), 200


@app.route("/world/longread/<int:longread_id>/edit_image", methods=["POST"])
def edit_longread_image(longread_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    longread = LongRead.query.get_or_404(longread_id)

    filename = uploaded_img.filename
    if filename != "":
        if longread.img_link != "/staticFiles/images/QuestionMark.jpg":
            os.remove(longread.img_link[1:])
        longread_img_name = "longread" + str(longread.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name))
        longread.img_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name)

        db.session.add(longread)
        db.session.commit()

    return jsonify({"message": "Longread image edit successfully"}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longread/blockcontent/all", methods=["POST"])
def blockcontents_longread_getAll():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    blockcontents_json = [model_to_json(bc) for bc in longread.blockcontents]
    return jsonify(blockcontents_json)


@app.route("/longread/blockcontent/event", methods=["POST"])
def event():
    try:
        blockcontent_id = request.json["blockcontent_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    return jsonify(model_to_json(blockcontent))


@app.route("/longread/blockcontent/event/edit", methods=["POST"])
def event_edit():
    try:
        blockcontent_id = request.json["blockcontent_id"]
        coordx = request.json["coordx"]
        coordy = request.json["coordy"]
        time = request.json["time"]
        floating_text = request.json["floating_text"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    blockcontent.coordx = coordx
    blockcontent.coordy = coordy
    blockcontent.time = time 
    blockcontent.floating_text = floating_text

    db.session.add(blockcontent)
    db.session.commit()

    return jsonify({"message": "Event edit successfully."}), 200


@app.route("/longread/blockcontent/event/delete", methods=["POST"])
def event_delete():
    try:
        blockcontent_id = request.json["blockcontent_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    blockcontent = BlockContent.query.get_or_404(blockcontent_id)
    blockcontent.coordx = None
    blockcontent.coordy = None
    blockcontent.time = None
    blockcontent.floating_text = None

    db.session.add(blockcontent)
    db.session.commit()

    return jsonify({"message": "Event delete successfully."}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longread/map", methods=["POST"])
def map():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    return jsonify(longread.map_link)


@app.route("/longread/map/<int:longread_id>/edit", methods=["POST"])
def map_edit(longread_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    longread = LongRead.query.get_or_404(longread_id)

    filename = uploaded_img.filename
    if filename != "":
        if longread.map_link != "/staticFiles/images/map_base.jpg":
            os.remove(longread.img_link[1:])
        longread_img_name = "map" + str(longread.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name))
        longread.map_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name)

        db.session.add(longread)
        db.session.commit()

    return jsonify({"message": "Map edit successfully."}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/longread/timeline", methods=["POST"])
def timeline():
    try:
        longread_id = request.json["longread_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    longread = LongRead.query.get_or_404(longread_id)
    return jsonify(longread.timeline_link)


@app.route("/longread/timeline/<int:longread_id>/edit", methods=["POST"])
def timeline_edit(longread_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    longread = LongRead.query.get_or_404(longread_id)

    filename = uploaded_img.filename
    if filename != "":
        if longread.timeline_link != "/staticFiles/images/timeline_base.jpg":
            os.remove(longread.img_link[1:])
        longread_img_name = "timeline" + str(longread.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name))
        longread.timeline_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], longread_img_name)

        db.session.add(longread)
        db.session.commit()

    return jsonify({"message": "Timeline edit successfully"}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/worlds/all", methods=["POST"])
def worlds():
    worlds = World.query.all()
    worlds_json = [model_to_json(w) for w in worlds]
    return jsonify(worlds_json)


@app.route("/world", methods=["POST"])
def world():
    try:
        world_id = request.json["world_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    world = World.query.get_or_404(world_id)
    return jsonify(model_to_json(world))


@app.route("/world/create", methods=["POST"])
def world_create():
    try:
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    world = World(name=name,
                  description=description,
                  img_link = "/staticFiles/images/world_base.jpg")

    db.session.add(world)
    db.session.commit()

    return jsonify({"message": "World create successfully."}), 201


@app.route("/world/edit", methods=["POST"])
def world_edit():
    try:
        world_id = request.json["world_id"]
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400
    
    world = World.query.get_or_404(world_id)
    world.name = name
    world.description = description

    db.session.add(world)
    db.session.commit()

    return jsonify({"message": "World edit successfully."}), 200


@app.route("/world/delete", methods=["POST"])
def world_delete():
    try:
        world_id = request.json["world_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    world = World.query.get_or_404(world_id)
    for longread in world.longreads:
        longread_delete(longread.id)
    for worldobj in world.worldobjs:
        worldobj_delete(worldobj.id)
    if world.img_link != "/staticFiles/images/QuestionMark.jpg":
        os.remove(world.img_link[1:])

    db.session.delete(world)
    db.session.commit()

    return jsonify({"message": "World delete successfully."}), 200


@app.route("/world/<int:world_id>/edit_image", methods=["POST"])
def edit_world_image(world_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    world = World.query.get_or_404(world_id)

    filename = uploaded_img.filename
    if filename != "":
        if world.img_link != "/staticFiles/images/world_base.jpg":
            os.remove(world.img_link[1:])
        world_img_name = "world" + str(world.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], world_img_name))
        world.img_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], world_img_name)

        db.session.add(world)
        db.session.commit()

    return jsonify({"message": "World image edit successfully."}), 200


# _______________________________________________________________________________________________________
# _______________________________________________________________________________________________________


@app.route("/world/worldobj/all", methods=["POST"])
def worldobj_getAll():
    try:
        world_id = request.json["world_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    world = World.query.get_or_404(world_id)
    worldobjs = [model_to_json(wo) for wo in world.worldobjs]
    return jsonify(worldobjs)


@app.route("/world/worldobj", methods=["POST"])
def worldobj():
    try:
        worldobj_id = request.json["worldobj_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400
    
    worldobj = WorldObj.query.get_or_404(worldobj_id)
    return jsonify(model_to_json(worldobj))


@app.route("/world/worldobj/create", methods=["POST"])
def worldobj_create():
    try:
        world_id = request.json["world_id"]
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    worldobj = WorldObj(world_id=world_id,
                        name=name,
                        description=description,
                        img_link = "/staticFiles/images/worldobj_base.jpg")

    db.session.add(worldobj)
    db.session.commit()

    return jsonify({"message": "World object create successfully."}), 201


@app.route("/world/worldobj/edit", methods=["POST"])
def worldobj_edit():
    try:
        worldobj_id = request.json["worldobj_id"]
        name = request.json["name"]
        description = request.json["description"]

    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400

    worldobj = WorldObj.query.get_or_404(worldobj_id)
    worldobj.name = name
    worldobj.description = description

    db.session.add(worldobj)
    db.session.commit()

    return jsonify({"message": "World object edit successfully."}), 200


@app.route("/world/worldobj/delete", methods=["POST"])
def worldobj_delete():
    try:
        worldobj_id = request.json["worldobj_id"]
    except KeyError:
        return jsonify({"error": "Invalid JSON data. Missing any key."}), 400
    
    worldobj = WorldObj.query.get_or_404(worldobj_id)
    if worldobj.img_link != "/staticFiles/images/worldobj_base.jpg":
        os.remove(worldobj.img_link[1:])

    db.session.delete(worldobj)
    db.session.commit()

    return jsonify({"message": "World object delete successfully."}), 200


@app.route("/world/worldobj/<int:worldobj_id>/edit_image", methods=["POST"])
def edit_worldobj_image(worldobj_id):
    try:
        uploaded_img = request.files["uploaded-file"]
    except Exception as e:
        return jsonify({"error": e}), 400

    worldobj = WorldObj.query.get_or_404(worldobj_id)

    filename = uploaded_img.filename
    if filename != "":
        if worldobj.img_link != "/staticFiles/images/worldobj_base.jpg":
            os.remove(worldobj.img_link[1:])
        worldobj_img_name = "worldobj" + str(worldobj.id) + ".jpg"
        uploaded_img.save(os.path.join(app.config["UPLOAD_FOLDER"], worldobj_img_name))
        worldobj.img_link = "/" + os.path.join(app.config["UPLOAD_FOLDER"], worldobj_img_name)

        db.session.add(worldobj)
        db.session.commit()

    return jsonify({"message": "World object image edit successfully."}), 200

