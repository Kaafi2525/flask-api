# rules of a ReST API
# 1. Data transfered from one application to another in key:value pairs called JSON.
# 2. You have to define a route or URL
# 3. You difine a method e.g GET, POST, PUT, PATCH, DELETE
# 4. You define status code for the app receiving the data know how to handle the data e.g 404,200,403

from flask import Flask,jsonify,request
from flask_jwt_extended import JWTManager,create_access_token, jwt_required
from models import db,Product,Sales,Purchases,User
from flask_cors import CORS
from sqlalchemy import func
import sentry_sdk

app = Flask(__name__)
CORS(app)

sentry_sdk.init(
    dsn="https://ecacd9b13390c362f783f0dce97fafe3@o4510538809671680.ingest.de.sentry.io/4510539001495632",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Mohamed2525@localhost:5432/expense_flask'

db.init_app(app)

# configure JWT
app.config['JWT_SECRET_KEY'] = 'hh123hsggdfrrd23yt'
jwt = JWTManager(app)


@app.route("/", methods=["GET"] )
def home():
    
    return jsonify({"Flask API" : "1.0"}), 200

@app.route("/products", methods=["GET","POST"] )
@jwt_required()
def products():
    if request.method == "GET":
        myproducts = Product.query.all() 
        products_list = []
        for product in myproducts:
            products_list.append({
                "id": product.id,
                "name": product.name,
                "buying_price": product.buying_price,
                "selling_price": product.selling_price
            })   
        return jsonify(products_list), 200
    
    elif request.method == "POST":
        data = request.get_json()
         # Check if product already exists by name
        existing_product = Product.query.filter_by(name=data['name']).first()
        if existing_product:
            return jsonify({
                "error": "Product already exists",
                "id": existing_product.id
            }), 409  # 409 Conflict
        new_product=Product(
            name=data['name'],
            buying_price=data['buying_price'],
            selling_price=data['selling_price']
        )
        db.session.add(new_product)
        db.session.commit()
        data['id'] = new_product.id
        return jsonify({"message": "Product added successfully"}), 201
    
    else:
        error = {"message": "Method not allowed"}
        return jsonify(error), 405

@app.route("/sales", methods=["GET","POST"] )
def sales():
    if request.method == "GET":
        mysales = Sales.query.all() 
        sales_list = []
        for sale in mysales:
            sales_list.append({
                "id": sale.id,
                "product_id": sale.product_id,
                "quantity": sale.quantity,
                "created_at": sale.created_at
            })   
        return jsonify(sales_list), 200
    
    elif request.method == "POST":
        data = request.get_json()
        new_sale=Sales(
            product_id=data['product_id'],
            quantity=data['quantity']
        )
        db.session.add(new_sale)
        db.session.commit()
        data['id'] = new_sale.id
        data['created_at'] = new_sale.created_at
        return jsonify({"message": "Sale recorded successfully"}), 201
    
    else:
        error = {"message": "Method not allowed"}
        return jsonify(error), 405

@app.route("/purchases", methods=["GET","POST"] )
def purchases():
    if request.method == "GET":
        mypurchases = Purchases.query.all() 
        purchases_list = []
        for purchase in mypurchases:
            purchases_list.append({
                "id": purchase.id,
                "product_id": purchase.product_id,
                "stock_quantity": purchase.stock_quantity,
                "created_at": purchase.created_at
            })   
        return jsonify(purchases_list), 200
    
    elif request.method == "POST":
        data = request.get_json()
        new_purchase=Purchases(
            product_id=data['product_id'],
            stock_quantity=data['stock_quantity']
        )
        db.session.add(new_purchase)
        db.session.commit()
        data['id'] = new_purchase.id
        data['created_at'] = new_purchase.created_at
        return jsonify({"message": "Purchase recorded successfully"}), 201
    
    else:
        error = {"message": "Method not allowed"}
        return jsonify(error), 405

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    new_user = User(
        username=data['username'],
        password=data['password'],
        email=data['email']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    # Validate JSON body
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    # Query user using email only (safer + avoids weird query issues)
    usr = User.query.filter_by(email=data["email"]).first()

    # Check credentials manually
    if usr is None or usr.password != data["password"]:
        return jsonify({"error": "Invalid email or password"}), 401

    # Create token using user.id or email
    token = create_access_token(identity=data["email"])

    return jsonify({"token": token}), 200


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    usr = User.query.filter_by(email=data["email"]).first() 
    if usr is None:
            error = {"error": "Email not found"}
            return jsonify(error), 404
    else:
            # In a real application, you would send an email with a reset link here
            return jsonify({"message": "Password reset link has been sent to your email"}), 200

    # usr = User.query.filter_by(email=data["email"], password=data["password"]).first() 
    # if usr is None:
    #     error = {"error": "Invalid email or password"}
    #     return jsonify(error), 401
    # else:
    #     token = create_access_token(identity = data["email"])
    #     return jsonify({"token": token}), 200 

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if request.method == "GET":
        remaining_stock_query =(
            db.session.query(
                Product.id,
                Product.name,
                (func.coalesce(func.sum(Purchases.stock_quantity), 0) - func.coalesce(func.sum(Sales.quantity), 0)).label('remaining_stock')
            )
            .outerjoin(Purchases, Product.id == Purchases.product_id)
            .outerjoin(Sales, Product.id == Sales.product_id)
            .group_by(Product.id, Product.name)
        )
    result = remaining_stock_query.all()
    print(result)
    data = []
    labels = []
    for r in result:
        data.append(r.remaining_stock)
        labels.append(r.name)
        return jsonify({"data": data, "labels": labels}), 200
    else:
        error = {"message": "Method not allowed"}
        return jsonify(error), 405






if __name__ == "__main__":
    with app.app_context():
        db.create_all()
app.run(debug=True)

