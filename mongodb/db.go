package mongodb

import (
	"context"
	"main/defines"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var Client *mongo.Client

func Connect() {

	Client, _ = mongo.Connect(context.TODO(), options.Client().ApplyURI(defines.DbURI))

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
