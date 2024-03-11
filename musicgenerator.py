# -*- coding: utf-8 -*-
"""MusicGenerator.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1pSQq9NGXt-4i2Aet-bePR3aP4EjKu7iA
"""

!pip install mido

# For playing midi files on Google Colab
!apt install fluidsynth
!cp /usr/share/sounds/sf2/FluidR3_GM.sf2 ./font.sf2
!pip install midi2audio

from midi2audio import FluidSynth
from IPython.display import Audio

def play_midi(midi_filename):
    """Call `play_midi` with a path to a midi file will show a midi player on Google Colab."""
    FluidSynth("font.sf2").midi_to_audio(midi_filename, 'test.wav')
    return Audio("test.wav")

import numpy as np
import random
import matplotlib.pyplot as plt

# Download tutorial data files.
!wget https://www.cs.toronto.edu/~lczhang/311/lab06/data.zip

# Unzip the zip file.
!unzip data.zip

play_midi('data/chopin/chpn-p1_simplified.mid')

play_midi('data/chopin/chpn-p1.mid')

from mido import MidiFile, MidiTrack

def get_midi_file_notes(filename):
    """Returns the sequence of notes played in the midi file
    There are 128 possible notes on a MIDI device, and they are numbered 0 to 127.
    The middle C is note number 60. Larger numbers indiciate higher pitch notes,
    and lower numbers indicate lower pitch notes.

    """
    notes = []
    for msg in  MidiFile(filename):
        if msg.type == 'note_on':
            notes.append(msg.note)
    return notes

print(get_midi_file_notes('data/chopin/chpn-p1_simplified.mid'))
print(get_midi_file_notes('data/chopin/chpn-p2_simplified.mid'))

CONTEXT_LENGTH = 20

def gen_input_output(notes, context_length=CONTEXT_LENGTH):
    """
    Generate a list of training data points, each of the form (x, t),
    where "x" is a list of length `context_length` consisting of the
    previous notes, and "t" is the corresponding next note.

    Parameters:
        `notes` - a sequence of notes in a piece, generated
                  from calling `get_midi_file_notes`
        `context_length` - length of each context

    Returns: a list of training pairs (x, t), with len(x) == context_length
    """
    D = []
    for i in range(len(notes) - context_length):
        seq = notes[i:i+context_length]
        next_note = notes[i+context_length]
        D.append((seq, next_note),)

    D.append((notes[-context_length:], 0),)

    return D

notes_chpnop23 = get_midi_file_notes('data/chopin/chpn_op23_simplified.mid')

D_chpnop23 = gen_input_output(notes=notes_chpnop23) # TODO

print(len(notes_chpnop23))
print(len(D_chpnop23) + CONTEXT_LENGTH - 1)

def make_onehot(indicies, total=128):
    """
    Convert indicies into one-hot vectors by
    first creating an identity matrix of shape [total, total],
    then indexing the appropriate columns of that identity matrix.

    Parameters:
        `indices` - a numpy array of some shape where
                    the value in these arrays should correspond to category
                    indices (e.g. note values between 0-127)
        `total` - the total number of categories (e.g. total number of notes)

    Returns: a numpy array of one-hot vectors
        If the `indices` array is shaped (N,)
           then the returned array will be shaped (N, total)
        If the `indices` array is shaped (N, D)
           then the returned array will be shaped (N, D, total)
        ... and so on.
    """
    I = np.eye(total)
    indicies = np.rint(indicies).astype(int)
    return I[indicies]

def get_X_t(D):
    """
    Generate the data matrix "X" and target vector "t" from a data set "D",

    Parameters:
        `D` - a list of pairs of the form (x, t), returned from
              the function `gen_input_output`

    Returns: a tuple (X, t) where
        `X` - a numpy array of shape (N, D), the data matrix
        `t` - a numpy array of shape (N,),
              with each value representing the index of the target note
    """
    t = np.array([next_note for seq, next_note in D])
    X_ids = np.array([seq for seq, next_note in D])
    X = make_onehot(X_ids)
    X = X.reshape(X.shape[0], -1)
    return X,t

X_chpnop23, t_chpnop23 = get_X_t(D_chpnop23)
X_chpnop23.shape

def softmax(z):
    """
    Compute the softmax of vector z, or row-wise for a matrix z.
    For numerical stability, subtract the maximum logit value from each
    row prior to exponentiation (see above).

    Parameters:
        `z` - a numpy array of shape (K,) or (N, K)

    Returns: a numpy array with the same shape as `z`, with the softmax
        activation applied to each row of `z`
    """
    # print(z.shape, "This is z")
    z -= np.max(z, axis=None if len(z.shape) == 1 else 1, keepdims=True)
    exp_z = np.exp(z)
    sum_exp_z = np.sum(exp_z, axis=None if len(z.shape) == 1 else 1, keepdims=True)
    softmax_z = exp_z / sum_exp_z
    # print(softmax_z.shape, "This is the soft max")
    return softmax_z

class MLPModel(object):
    def __init__(self, num_features=128*20, num_hidden=100, num_classes=128):
        """
        Initialize the weights and biases of this two-layer MLP.
        """
        # information about the model architecture
        self.num_features = num_features
        self.num_hidden = num_hidden
        self.num_classes = num_classes

        # weights and biases for the first layer of the MLP
        self.W1 = np.zeros([num_features, num_hidden])
        self.b1 = np.zeros([num_hidden])

        # weights and biases for the second layer of the MLP
        self.W2 = np.zeros([num_hidden, num_classes])
        self.b2 = np.zeros([num_classes])

        # initialize the weights and biases
        self.initializeParams()

        # set all values of intermediate variables (to be used in the
        # forward/backward passes) to None
        self.cleanup()

    def initializeParams(self):
        """
        Initialize the weights and biases of this two-layer MLP to be random.
        This random initialization is necessary to break the symmetry in the
        gradient descent update for our hidden weights and biases.
        """
        self.W1 = np.random.normal(0, 2/self.num_features, self.W1.shape)
        self.b1 = np.random.normal(0, 2/self.num_features, self.b1.shape)
        self.W2 = np.random.normal(0, 2/self.num_hidden, self.W2.shape)
        self.b2 = np.random.normal(0, 2/self.num_hidden, self.b2.shape)

    def forward(self, X):
        """
        Compute the forward pass to produce prediction for inputs.

        Parameters:
            `X` - A numpy array of shape (N, self.num_features)

        Returns: A numpy array of predictions of shape (N, self.num_classes)
        """
        return do_forward_pass(self, X) # To be implemented below

    def backward(self, ts):
        """
        Compute the backward pass, given the ground-truth, one-hot targets.

        Parameters:
            `ts` - A numpy array of shape (N, self.num_classes)
        """
        return do_backward_pass(self, ts) # To be implemented below

    def loss(self, ts):
        """
        Compute the average cross-entropy loss, given the ground-truth, one-hot targets.

        Parameters:
            `ts` - A numpy array of shape (N, self.num_classes)
        """
        return np.sum(-ts * np.log(self.y)) / ts.shape[0]

    def update(self, alpha):
        """
        Compute the gradient descent update for the parameters of this model.

        Parameters:
            `alpha` - A number representing the learning rate
        """
        self.W1 = self.W1 - alpha * self.W1_bar
        self.b1 = self.b1 - alpha * self.b1_bar
        self.W2 = self.W2 - alpha * self.W2_bar
        self.b2 = self.b2 - alpha * self.b2_bar

    def cleanup(self):
        """
        Erase the values of the variables that we use in our computation.
        """
        # To be filled in during the forward pass
        self.N = None # Number of data points in the batch
        self.X = None # The input matrix
        self.m = None # Pre-activation value of the hidden state, should have shape
        self.h = None # Post-RELU value of the hidden state
        self.z = None # The logit scores (pre-activation output values)
        self.y = None # Class probabilities (post-activation)
        # To be filled in during the backward pass
        self.z_bar = None # The error signal for self.z2
        self.W2_bar = None # The error signal for self.W2
        self.b2_bar = None # The error signal for self.b2
        self.h_bar = None  # The error signal for self.h
        self.m_bar = None # The error signal for self.z1
        self.W1_bar = None # The error signal for self.W1
        self.b1_bar = None # The error signal for self.b1

def do_forward_pass(model, X):
    """
    Compute the forward pass to produce prediction for inputs.

    This function also keeps some of the intermediate values in
    the neural network computation, to make computing gradients easier.

    For the ReLU activation, you may find the function `np.maximum` helpful

    Parameters:
        `model` - An instance of the class MLPModel
        `X` - A numpy array of shape (N, model.num_features)

    Returns: A numpy array of predictions of shape (N, model.num_classes)
    """
    model.N = X.shape[0]
    model.X = X
    model.m = np.dot( X, model.W1) + model.b1
    model.h = np.maximum(0, model.m)
    # print(model.h.shape, model.W2.shape, model.b2.shape, "Who is the problem? W2 answered")
    model.z = np.dot(  model.h, model.W2) + model.b2
    model.y = softmax(model.z)
    return model.y

def generate_piece(model, seed, max_len=100):
    """
    Generate a piece of music given the model and an initial
    "seed" sequence of notes at the beginning of the piece.

    The piece is generated one note at a time by using, as input
    to the model, the previous 20 notes. The model outputs a
    probability distribution over the next possible note, and we
    will take the most probable note as the next note in our piece.

    Parameters:
        `model` - an instance of MLPModel
        `seed` - a sequence of notes at the beginning of a piece,
                 e.g. generated from calling `get_midi_file_notes`
                 must be at least as long as CONTEXT_LENGTH
        `max_len` - maximum number of total notes in the piece.

    Returns: a list of sequence of notes with length at most `max_len`
    """
    assert(len(seed) >= CONTEXT_LENGTH)

    generated = seed
    while len(generated) < max_len:
        last_n_notes = generated[-CONTEXT_LENGTH:]
        X = make_onehot(last_n_notes).reshape((1, -1))

        y = do_forward_pass(model, X)

        next_note = np.argmax(y)
        if next_note == 0: # Look for the marker for the end of the song
            break
        generated.append(next_note)

    return generated

def generate_midi(notes, outfile):
    from mido import MidiFile, MidiTrack, Message

    new_mid = MidiFile()
    new_track = MidiTrack()
    new_mid.tracks.append(new_track)

    for note in notes:
        new_track.append(Message('note_on', note=note, velocity=64, time=128))
    new_mid.save(outfile)

seed = notes_chpnop23[:CONTEXT_LENGTH]
notes = generate_piece(MLPModel(), seed, CONTEXT_LENGTH * 2)
print(notes)
generate_midi(notes, 'chpnop23_untrained.mid')
play_midi('chpnop23_untrained.mid')

seed = notes_chpnop23[:CONTEXT_LENGTH] #Original piece
generate_midi(seed, 'chpnop23_seed.mid')
play_midi('chpnop23_seed.mid')

def do_backward_pass(model, ts):
    """
    Compute the backward pass, given the ground-truth, one-hot targets.

    Parameters:
        `model` - An instance of the class MLPModel
        `ts` - A numpy array of shape (N, model.num_classes)
    """
    model.z_bar = (model.y - ts) / model.N
    model.W2_bar = np.dot(np.transpose(model.h), model.z_bar)
    model.b2_bar = np.dot(np.ones(model.N), model.z_bar)
    model.h_bar = np.dot(model.z_bar, model.W2.T)
    model.m_bar = model.h_bar * (model.m > 0)
    model.W1_bar = np.dot(model.X.T, model.m_bar)
    model.b1_bar = np.dot(np.ones(model.N), model.m_bar)

def train_sgd(model, X_train, t_train,
              alpha=0.1, n_epochs=0, batch_size=100,
              X_valid=None, t_valid=None,
              w_init=None, plot=True):
    '''
    Given `model` - an instance of MLPModel
          `X_train` - the data matrix to use for training
          `t_train` - the target vector to use for training
          `alpha` - the learning rate.
                    From our experiments, it appears that a larger learning rate
                    is appropriate for this task.
          `n_epochs` - the number of **epochs** of gradient descent to run
          `batch_size` - the size of each mini batch
          `X_valid` - the data matrix to use for validation (optional)
          `t_valid` - the target vector to use for validation (optional)
          `w_init` - the initial `w` vector (if `None`, use a vector of all zeros)
          `plot` - whether to track statistics and plot the training curve

    Solves for model weights via stochastic gradient descent,
    using the provided batch_size.

    Return weights after `niter` iterations.
    '''
    # as before, initialize all the weights to zeros
    w = np.zeros(X_train.shape[1])

    train_loss = [] # for the current minibatch, tracked once per iteration
    valid_loss = [] # for the entire validation data set, tracked once per epoch

    # track the number of iterations
    niter = 0

    N = X_train.shape[0] # number of training data points
    indices = list(range(N))

    for e in range(n_epochs):
        random.shuffle(indices) # for creating new minibatches

        for i in range(0, N, batch_size):
            if (i + batch_size) > N:
                continue

            indices_in_batch = indices[i: i+batch_size]
            X_minibatch = X_train[indices_in_batch, :]
            t_minibatch = make_onehot(t_train[indices_in_batch], 128)

            # gradient descent iteration
            model.cleanup()
            model.forward(X_minibatch)
            model.backward(t_minibatch)
            model.update(alpha)

            if plot:
                # Record the current training loss values
                train_loss.append(model.loss(t_minibatch))
            niter += 1

        # compute validation data metrics, if provided, once per epoch
        if plot and (X_valid is not None) and (t_valid is not None):
            model.cleanup()
            model.forward(X_valid)
            valid_loss.append((niter, model.loss(make_onehot(t_valid))))

    if plot:
        plt.title("SGD Training Curve Showing Loss at each Iteration")
        plt.plot(train_loss, label="Training Loss")
        if (X_valid is not None) and (t_valid is not None): # compute validation data metrics, if provided
            plt.plot([iter for (iter, loss) in valid_loss],
                     [loss for (iter, loss) in valid_loss],
                     label="Validation Loss")
        plt.xlabel("Iterations")
        plt.ylabel("Loss")
        plt.legend()
        plt.show()
        print("Final Training Loss:", train_loss[-1])
        if (X_valid is not None) and (t_valid is not None):
            print("Final Validation Loss:", valid_loss[-1])

# produce a single batch of data
X_small = X_chpnop23[:100]
t_small = t_chpnop23[:100]
model = MLPModel()
train_sgd(model, X_train=X_small, t_train=t_small, alpha=0.2, batch_size=100, n_epochs=500)

def generate_data_for_files(files):
    Xs, ts = [], []
    for file in files:
        notes = get_midi_file_notes(file)
        D = gen_input_output(notes)
        X, t = get_X_t(D)
        Xs.append(X)
        ts.append(t)
    X = np.concatenate(Xs, axis=0)
    t = np.concatenate(ts, axis=0)
    return X, t

import glob
files = [file for file in glob.glob('data/chopin/*_simplified.mid')]
X_train, t_train = generate_data_for_files(files[:30])
X_valid, t_valid = generate_data_for_files(files[30:])

model = MLPModel()
train_sgd(model, alpha=0.1, X_train=X_train, t_train=t_train, X_valid=X_valid, t_valid=t_valid, batch_size=100, n_epochs=30)

seed = notes_chpnop23[:CONTEXT_LENGTH]

notes = None # TODO
generate_midi(notes, 'chpnop23_comp.mid')
play_midi('chpnop23_comp.mid')