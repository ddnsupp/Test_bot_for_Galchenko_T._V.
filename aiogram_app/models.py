from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    t_id = Column(BigInteger, nullable=False)
    username = Column(String(255))
    phone = Column(String(30))
    address = Column(String(255))
    user_type = Column(String(20), default='Customer')
    messages_to_delete = Column(ARRAY(Integer), default=[], nullable=False)
    carts = relationship('Cart', back_populates='user')


class Subcategory(Base):
    __tablename__ = 'subcategory'
    subcategory_id = Column(Integer, primary_key=True, autoincrement=True)
    subcategory_name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey('category.category_id'), nullable=False)
    category = relationship('Category', back_populates='subcategories')


class Category(Base):
    __tablename__ = 'category'
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    subcategories = relationship('Subcategory', back_populates='category')


class Product(Base):
    __tablename__ = 'product'
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('category.category_id'), nullable=False)
    subcategory_id = Column(Integer, ForeignKey('subcategory.subcategory_id'), nullable=False)
    product_name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    photos = relationship('ProductPhoto', back_populates='product')
    cart_products = relationship('CartProduct', back_populates='product')


class ProductPhoto(Base):
    __tablename__ = 'product_photo'
    product_photo_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(255))
    product_id = Column(Integer, ForeignKey('product.product_id'))
    product = relationship('Product', back_populates='photos')


class Cart(Base):
    __tablename__ = 'cart'
    cart_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.user_id'))  # Изменено на UUID
    user = relationship('User', back_populates='carts')
    cart_products = relationship('CartProduct', back_populates='cart')


class CartProduct(Base):
    __tablename__ = 'cart_product'
    cart_product_id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey('cart.cart_id'))
    product_id = Column(Integer, ForeignKey('product.product_id'))
    quantity = Column(Integer, nullable=False)
    cart = relationship('Cart', back_populates='cart_products')
    product = relationship('Product', back_populates='cart_products')


class Newsletter(Base):
    __tablename__ = 'newsletters'
    newsletter_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_on = Column(TIMESTAMP, nullable=False)
