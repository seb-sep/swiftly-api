/* global use, db */
// MongoDB Playground
// To disable this template go to Settings | MongoDB | Use Default Template For Playground.
// Make sure you are connected to enable completions and to be able to run a playground.
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.
// The result of the last command run in a playground is shown on the results panel.
// By default the first 20 documents will be returned with a cursor.
// Use 'console.log()' to print to the debug output.
// For more documentation on playgrounds please refer to
// https://www.mongodb.com/docs/mongodb-vscode/playgrounds/

// Select the database to use.
use('test');


// add date created to each note
db.user.find({}).forEach((doc) => {
    const updated = doc.notes.map((note) => {
        if (!note.created) {
            return { ...note, created: new Date(0) }
        }
        return note;
    });

    db.user.updateOne({ _id: doc._id}, { $set: { notes: updated } });
});

// add favorite to each note
db.user.find({}).forEach((doc) => {
    const updated = doc.notes.map((note) => {
        if (!note.favorite) {
            return { ...note, favorite: false }
        }
        return note;
    });

    db.user.updateOne({ _id: doc._id}, { $set: { notes: updated } });
});