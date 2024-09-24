package mongodb

import (
	"context"
	"fmt"
	"os"

	"github.com/joho/godotenv"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var Client *mongo.Client

func Connect() {
	err := godotenv.Load()
	if err != nil {
		fmt.Println("Error loading .env file")
		panic(err)
	}
	uri := os.Getenv("MONGODB_URI")
	Client, _ = mongo.Connect(context.TODO(), options.Client().ApplyURI(uri))

	// defer func() {
	// 	if err := Client.Disconnect(context.TODO()); err != nil {
	// 		panic(err)
	// 	}
	// }()
}

func Disconnect() {
	if err := Client.Disconnect(context.TODO()); err != nil {
		panic(err)
	}
}
