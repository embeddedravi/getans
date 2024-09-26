package model

import (
	"context"
	"encoding/base64"
	"getans/mongodb"

	"go.mongodb.org/mongo-driver/bson"
	"golang.org/x/crypto/bcrypt"
)

type MdlUserSignupForm struct {
	FirstName string `json:"first_name" bson:"first_name" validate:"required min=3 max=30"`
	LastName  string `json:"last_name" bson:"last_name" validate:"required min=3 max=30"`
	Mobile    string `json:"mobile" bson:"mobile" validate:"required"`
	Email     string `json:"email" bson:"email" validate:"required,email"`
	Password  string `json:"password" bson:"password" validate:"required"`
	Gender    string `json:"gender" bson:"gender" validate:"required oneof=male female other"`
	Dob       string `json:"dob" bson:"dob" validate:"required"`
	Terms     bool   `json:"terms"  validate:"required"`
}

type MdlUserDetails struct {
	FirstName string `json:"firstname" bson:"firstname" validate:"required min=3 max=30"`
	LastName  string `json:"lastname" bson:"lastname" validate:"required min=3 max=30"`
	Mobile    string `json:"mobile" bson:"mobile" validate:"required"`
	Email     string `json:"email" bson:"email" validate:"required,email"`
	Password  string `json:"password" bson:"password" validate:"required"`
	Gender    string `json:"gender" bson:"gender" validate:"required oneof=male female other"`
	Dob       string `json:"dob" bson:"dob" validate:"required"`
	Verified  bool   `json:"verified" bson:"verified"`
	Status    string `json:"status" bson:"status"`
	Type      string `json:"type" bson:"type"`
	CreatedAt string `json:"created_at" bson:"created_at"`
	UpdatedAt string `json:"updated_at" bson:"updated_at"`
}

type MdlUserSigninForm struct {
	Email    string `json:"email" bson:"email" validate:"required"`
	Password string `json:"password" bson:"password" validate:"required"`
	Terms    bool   `json:"terms" bson:"terms" validate:"required"`
}

func HashPassword(password string) (string, error) {
	// Hash the password with the salt
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}
	// fmt.Fprint(os.Stdout, "password: "+password+"\n"+"saltc: "+base64.StdEncoding.EncodeToString(salt)+"\n")
	// Return the salt and hashed password as separate strings
	return base64.StdEncoding.EncodeToString(hashedPassword), nil
}

func VerifyPassword(password string, hashedPassword string) bool {
	// Decode the salt value
	hashedPasswordBytes, err := base64.StdEncoding.DecodeString(hashedPassword)
	if err != nil {
		return false
	}
	// Directly compare the password with the stored hashed password
	err = bcrypt.CompareHashAndPassword([]byte(hashedPasswordBytes), []byte(password))
	return err == nil
}

func IsEmailRegistered(email string) bool {

	// Check if the email is already registered
	mongodb.Connect()
	coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
	defer mongodb.Disconnect()

	count, err := coll.CountDocuments(context.TODO(), bson.M{"email": email})
	return err == nil && count > 0
}
