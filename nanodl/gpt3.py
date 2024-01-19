'''
The motivation behind GPT is to create a highly effective language model that can understand and generate human-like text. 
Its architecture is a decoder-only transformer trained on next-token prediction and generates autoregressively duting training.
It's pre-trained on a massive amount of text data, which allows it to learn the patterns and nuances of language. 
GPT's strength lies in its ability to generalize this knowledge to perform a wide range of natural language processing tasks without the need for extensive task-specific training, 
making it a powerful tool for various applications in language understanding and generation.
GPT3 uses prelayer normalisation opposed to classic transformers

Note:
This implementation excludes the modified initialization which accounts for the accumulation on the residual path with model depth. 
Such an intialisation involves scaling the weights of residual layers at initialization by a factor of 1/√N where N is the number of residual layers. 
Rather we use 'Xavier' initialization (https://proceedings.mlr.press/v9/glorot10a.html) for the weights and 'zeros' for the biases.


example usage:
```
from gpt3 import *

# Dummy data parameters
batch_size = 8
max_length = 51
vocab_size = 1000 
embed_dim = 256 

# Generate dummy text and image data
data = jnp.arange(batch_size * max_length, dtype=jnp.int32).reshape((batch_size, max_length))
dummy_inputs = data[:, :-1]
dummy_targets = data[:, 1:]

# model parameters
hyperparams = {
    'num_layers': 1,
    'hidden_dim': 256,
    'num_heads': 2,
    'feedforward_dim': 256,
    'dropout': 0.1,
    'vocab_size': 1000,
    'embed_dim': 256,
    'max_length': max_length,
    'start_token': 0,
    'end_token': 50,
}

# Initialize model
model = GPT3(**hyperparams)
rngs = {'params': jax.random.key(0), 'dropout': jax.random.key(1)}
params = model.init(rngs, dummy_inputs)['params']
outputs = model.apply({'params': params}, dummy_inputs, rngs={'dropout': jax.random.PRNGKey(2)})
print(outputs.shape)

# Training on your data
dataloader = [(dummy_inputs, dummy_targets)] * 10
trainer = GPT3DataParallelTrainer(model, dummy_inputs.shape, 'params.pkl')
trainer.train(dataloader, num_epochs=2)
print(trainer.evaluate(dataloader))
```
'''

import jax
import time
import optax
import pickle
import jax.numpy as jnp
import flax.linen as nn
from flax.training import train_state
from typing import List, Tuple, Any, Optional, Iterable


class SelfMultiHeadAttention(nn.Module):
    """
    https://arxiv.org/abs/1706.03762 (Vaswani et. al. 2017)
    This involves transforming the input by weighting features by importance.
    """
    hidden_dim : int  # Output dimension
    num_heads : int  # Number of parallel heads

    def setup(self):
        # Stack all weight matrices together for efficiency
        self.projection = nn.Dense(3*self.hidden_dim,
                                 kernel_init=nn.initializers.xavier_uniform(),
                                 bias_init=nn.initializers.zeros 
                                )
        self.output = nn.Dense(self.hidden_dim,
                               kernel_init=nn.initializers.xavier_uniform(),
                               bias_init=nn.initializers.zeros)


    def __call__(self, 
                 inputs: jnp.ndarray, 
                 mask: jnp.ndarray = None) -> tuple:

        """
        Args:
            Inputs: ((batch_size, seq_len, dims))
            Mask: optional - masks where reqions to ignore are flipped to os
                  regions to attend to are 1s (batch_size, seq_len, dims)

        Return: outputs (batch_size, seq_len, seq_len)
                attention matrixes (batch_size, heads, seq_len, seq_len)
        """
        projections = self.projection(inputs)
        query, key, value = jnp.array_split(projections, 3, axis=-1)
        context_vectors, attention = self.attention_function(query,key, value, mask=mask)
        outputs = self.output(context_vectors)
        return outputs, attention
    
    def attention_function(self, query, key, value, mask=None):
        input_length = query.shape[1]
        context_length = key.shape[1]
        head_dim = query.shape[-1] // self.num_heads
        dim_key = key.shape[-1]

        # Split queries, keys, and values into heads
        query_heads = jnp.reshape(query, (query.shape[0], self.num_heads, input_length, head_dim))
        key_heads = jnp.reshape(key, (key.shape[0], self.num_heads, context_length, head_dim))
        value_heads = jnp.reshape(value, (value.shape[0], self.num_heads, context_length, head_dim))

        attention_scores = jnp.matmul(query_heads, key_heads.transpose(0, 1, 3, 2)) / jnp.sqrt(dim_key)
        if mask is not None:
            attention_scores = attention_scores * mask

        attention_weights = jax.nn.softmax(attention_scores, axis=-1)
        attended_values = jnp.matmul(attention_weights, value_heads)
        attended_values = jnp.reshape(attended_values, (query.shape[0], input_length, query.shape[-1]))
        return attended_values, attention_weights
    

class PositionWiseFFN(nn.Module):
    """
    Position-wise Feed-Forward Network.

    Args:
        num_hiddens (int): Number of hidden units in the feed-forward layers.
        num_outputs (int): Number of output units in the feed-forward layers.
    """
    num_hiddens: int
    num_outputs: int

    def setup(self):
        self.dense1 = nn.Dense(self.num_hiddens, kernel_init=nn.initializers.xavier_uniform())
        self.activation = GEGLU(self.num_hiddens)
        self.dense2 = nn.Dense(self.num_outputs, kernel_init=nn.initializers.xavier_uniform())

    def __call__(self, X: jnp.ndarray) -> jnp.ndarray:
        """
        Apply the PositionWiseFFN to input data.

        Args:
            X (jnp.ndarray): Input tensor.

        Returns:
            jnp.ndarray: Output tensor after applying the feed-forward network.
        """
        return self.dense2(self.activation(self.dense1(X)))


class GEGLU(nn.Module):
    """
    Gated GLU (Gated Linear Unit).
    GEGLU(x) = x * 0.5 * gate * (1 + tanh(gate * 0.7978845608 * (1 + 0.044715 * (gate**2))))

    Args:
        output_dim (int): Output dimension of the GLU layer.
    """
    output_dim: int

    def setup(self):
        self.dense = nn.Dense(self.output_dim * 2,
                              kernel_init=nn.initializers.xavier_uniform())

    def __call__(self, inputs):
        x = self.dense(inputs)
        x, gate = x[..., : self.output_dim], x[..., self.output_dim :]
        tanh_res = jnp.tanh(gate * 0.7978845608 * (1 + 0.044715 * (gate**2)))
        return x * 0.5 * gate * (1 + tanh_res)
    

class GPT3Block(nn.Module):
    """
    Transformer Decoder Block.

    Args:
        hidden_dim (int): Input dimension.
        num_heads (int): Number of attention heads.
        feedforward_dim (int): Dimension of the feed-forward network.
        dropout (float): Dropout rate.
    """
    hidden_dim: int
    num_heads: int
    feedforward_dim: int
    dropout: float

    def setup(self):
        self.attention1 = SelfMultiHeadAttention(hidden_dim=self.hidden_dim, num_heads=self.num_heads)
        self.attention2 = SelfMultiHeadAttention(hidden_dim=self.hidden_dim, num_heads=self.num_heads)
        self.feed_forward = PositionWiseFFN(self.feedforward_dim, self.hidden_dim)
        self.norm1 = nn.LayerNorm(self.dropout)
        self.norm2 = nn.LayerNorm(self.dropout)
        self.norm3 = nn.LayerNorm(self.dropout)
        self.dropout1 = nn.Dropout(self.dropout)
        self.dropout2 = nn.Dropout(self.dropout)
        self.dropout3 = nn.Dropout(self.dropout)

    def causal_mask(self, 
                batch_size: int, 
                destination_dim: int, 
                source_dim: int) -> jnp.ndarray:
        """
        Generate a causal mask for self-attention.

        Args:
            batch_size (int): Batch size.
            destination_dim (int): Dimension of the destination sequence.
            source_dim (int): Dimension of the source sequence.

        Returns:
            jnp.ndarray: Causal mask with shape (batch_size, num_heads, destination_dim, source_dim).
        """
        # Create index tensors for the source and destination dimensions
        idx_source = jnp.arange(destination_dim)[:, None]
        idx_destination = jnp.arange(source_dim)
        mask = idx_source >= idx_destination - source_dim + destination_dim
        mask = mask.astype(jnp.int32) 

        # Expand dimensions to match the required output shape
        mask = mask[None, None, :, :]
        return jnp.broadcast_to(mask, (batch_size, self.num_heads, destination_dim, source_dim))

    def __call__(self, 
                x: jnp.ndarray, 
                mask: jnp.ndarray = None, 
                training: bool = False) -> tuple:
        """
        Apply the DecoderBlock to input data.

        Args:
            x (jnp.ndarray): Input tensor.
            mask (jnp.ndarray, optional): Mask tensor. Defaults to None.
            training (bool): Training mode.

        Returns:
            tuple: Output tensor, attention tensor, and cross-attention tensor.
        """
        mask = self.causal_mask(x.shape[0], x.shape[1], x.shape[1])

        x = self.norm1(x)
        attended_x, attention1 = self.attention1(x, mask=mask)
        x = self.dropout1(x, deterministic=not training)
        x += attended_x

        x = self.norm2(x)
        attended_x, attention2 = self.attention2(x, mask=mask)
        x = self.dropout2(x, deterministic=not training)
        x += attended_x

        x = self.norm3(x)
        output = self.feed_forward(x)
        x = self.dropout3(output, deterministic=not training)
        x += attended_x

        return x, jnp.array(attention1), jnp.array(attention2)
    

class GPT3Decoder(nn.Module):
    """
    Transformer Decoder.

    Args:
        num_layers (int): Number of decoder layers.
        hidden_dim (int): Input dimension.
        num_heads (int): Number of attention heads.
        feedforward_dim (int): Dimension of the feed-forward network.
        dropout (float): Dropout rate.
    """
    num_layers: int
    hidden_dim: int
    num_heads: int
    feedforward_dim: int
    dropout: float
    vocab_size: float
    embed_dim: float


    def setup(self):
        self.embedding = nn.Embed(num_embeddings=self.vocab_size, 
                                  features=self.embed_dim)
        
        self.layers = [GPT3Block(self.hidden_dim, 
                                    self.num_heads, 
                                    self.feedforward_dim, 
                                    self.dropout) for _ in range(self.num_layers)]
        
        self.outputs = nn.Dense(self.vocab_size)
        

    def __call__(self, 
                 x: jnp.ndarray,
                 mask: jnp.ndarray = None, 
                 training: bool = False) -> tuple:
        """
        Apply the TransformerDecoder to input data.

        Args:
            x (jnp.ndarray): Input tensor.
            mask (jnp.ndarray, optional): Mask tensor. Defaults to None.
            training (bool): Training mode.

        Returns:
            tuple: Output tensor, list of attention tensors, and list of cross-attention tensors.
            each attention map has dim (num_layers, batch_size, num_heads, seq_length, seq_length)
        """
        attention_maps = []
        x = self.embedding(x)
        cross_attention_maps = []
        for layer in self.layers:
            x, attention, cross_attention = layer(x, mask=mask, training=training)
            attention_maps.append(attention)
            cross_attention_maps.append(cross_attention)
        return self.outputs(x), jnp.array(attention_maps), jnp.array(cross_attention_maps)
    

class GPT3(nn.Module):

    num_layers: int
    hidden_dim: int
    num_heads: int
    feedforward_dim: int
    dropout: float
    vocab_size: float
    embed_dim: float
    max_length: int
    start_token: int
    end_token: int

    """
    Decoder-only model from OpenAI's GPT-3 paper: https://arxiv.org/abs/2005.14165

    Args:
        num_layers (int): Number of layers in the encoder and decoder.
        num_heads (int): Number of attention heads in the multi-head attention layers.
        feedforward_dim (int): Dimensionality of the feedforward layers.
        dropout (float): Dropout probability.
        vocab_size (int): Size of the vocabulary.
        embed_dim (int): Dimensionality of embeddings.
        max_length (int): Maximum length of generated sequences.
        start_token (int): Token ID for the start of sequence.
        end_token (int): Token ID for the end of sequence.
    """

    def setup(self):
        """
        Initialize the T5 model by setting up the encoder and decoder.
        """
        self.decoder = GPT3Decoder(self.num_layers,
                                self.embed_dim,
                                self.num_heads,
                                self.feedforward_dim,
                                self.dropout,
                                self.vocab_size,
                                self.embed_dim)
        
        
    def __call__(self, 
                 x: jnp.ndarray,
                 training: bool = True) -> jnp.ndarray:
        
        """ 
        Causal models are trained differently, the outputs are just the inputs shifted by 1
        While the generation is autoregressve, hence a different function for that
        """
        return self.decoder(x=x, training=training)[0]


    def generate(self, 
                 x: Optional[jnp.ndarray] = None, 
                 temperature: float = 1.0,
                 training: bool = False) -> jnp.ndarray:
        """
        Generate sequences either from scratch or continues from the input sequence.

        Args:
            x (jax.numpy.ndarray): Input sequence.
            temperature (float, optional): Temperature for token sampling. Higher values result in more randomness.
            training (bool, optional): Whether the model is in training mode.

        Returns:
            tuple: A tuple containing the generated sequence.
        """

        # Initialize the decoding input with a special token
        decoder_input = x if x is not None else jnp.array([[self.start_token]])
        output_sequence = []

        # Autoregressive decoding loop
        for _ in range(self.max_length):
            decoder_output = self.decoder(x=decoder_input,
                                          training=training) 
            
            scaled_logits = decoder_output / temperature
            next_token_probabilities = jax.nn.softmax(scaled_logits, axis=-1)
            next_token = jax.random.categorical(jax.random.PRNGKey(0), next_token_probabilities, 1)[0]
            output_sequence.append(next_token.item())
            decoder_input = jnp.expand_dims(next_token, axis=1)
            if next_token.item() == self.end_token:
                break

        return output_sequence
    

class GPT3DataParallelTrainer:
    """
    A class for training a GPT model using data parallelism.

    Attributes:
        model: The GPT model to be trained.
        num_parameters: The number of parameters in the model.
        best_val_loss: The best validation loss achieved during training.
        weights_filename: Filename for saving the model weights.
        num_devices: Number of local devices (GPUs/TPUs) used for parallel training.
        state: The current state of the model, including parameters and optimizer state.
    """
    def __init__(self, 
                 model: Any, 
                 input_shape: Tuple[int, ...],
                 weights_filename: str,
                 learning_rate: float = 1e-5,
                 params_path: Optional[str] = None) -> None:
        self.model = model
        self.params_path = params_path
        self.num_parameters = None
        self.best_val_loss = float("inf")
        self.weights_filename = weights_filename
        self.num_devices = jax.local_device_count()
        self.train_step = jax.pmap(GPT3DataParallelTrainer.train_step, axis_name='devices')
        self.evaluation_step = jax.pmap(GPT3DataParallelTrainer.evaluation_step, axis_name='devices')
        self.state = self.create_train_state(learning_rate, input_shape)
        print(f'Number of accelerators: {self.num_devices}')
    

    def create_train_state(self, 
                           learning_rate: float, 
                           input_shape: Tuple[int, ...]) -> Any:
        """
        Creates and initializes the training state for the model.

        Args:
            learning_rate: The learning rate for the optimizer.
            text_input_shape: The shape of the text input.
            image_input_shape: The shape of the image input.

        Returns:
            The initialized training state.
        """
        rngs = {'params': jax.random.key(0), 'dropout': jax.random.key(1)}
        params = self.model.init(rngs, jnp.ones(input_shape, dtype=jnp.int32))['params']

        if self.params_path is not None:
            params = self.load_params(self.params_path)

        self.num_parameters = sum(param.size for param in jax.tree_util.tree_leaves(params))
        print(f'Number of parameters: {self.num_parameters}')
        state = train_state.TrainState.create(apply_fn=self.model.apply, 
                                              params=params, 
                                              tx=optax.adam(learning_rate))
        return jax.device_put_replicated(state, jax.local_devices())
    
    @staticmethod
    def train_step(state: Any, 
                   inputs: jnp.ndarray,
                   targets: jnp.ndarray) -> Tuple[Any, jnp.ndarray]:
        """
        Performs a single training step.

        Args:
            state: The current state of the model, including parameters and optimizer state.
            batch: A dictionary containing 'inputs' and 'targets' as keys, representing the input data.

        Returns:
            A tuple of the updated state and the loss value for this step.
        """
        def loss_fn(params):
            logits = state.apply_fn({'params': params}, 
                                    inputs, 
                                    training=True,
                                    rngs={'dropout': jax.random.PRNGKey(int(time.time()))})
            return optax.softmax_cross_entropy_with_integer_labels(logits, targets).mean()
        
        loss, grads = jax.value_and_grad(loss_fn)(state.params)
        state = state.apply_gradients(grads=grads)
        return state, loss

    def train(self, 
              train_loader: Iterable[Tuple[jnp.ndarray, jnp.ndarray]], 
              num_epochs: int, 
              val_loader: Optional[Iterable[Tuple[jnp.ndarray, jnp.ndarray]]] = None) -> None:
        """
        Trains the model for a specified number of epochs.

        Args:
            train_loader: An iterable of training data batches.
            num_epochs: The number of epochs to train for.
            val_loader: An optional iterable of validation data batches.
        """
        for epoch in range(num_epochs):
            total_loss = 0.0
            count = 0
            for inputs, targets in train_loader:
                batch_size = inputs.shape[0]
                batch_size_per_device = batch_size // self.num_devices
                inputs = inputs.reshape((self.num_devices, batch_size_per_device, -1))
                targets = targets.reshape((self.num_devices, batch_size_per_device, -1))
                self.state, loss = self.train_step(state=self.state, 
                                                   inputs=inputs, 
                                                   targets=targets)
                total_loss += jnp.mean(loss)
                count += 1
            
            mean_loss = total_loss / count
            print(f'Epoch {epoch+1}, Train Loss: {mean_loss}')

            if val_loader is not None:
                val_loss = self.evaluate(val_loader)
                print(f'Epoch {epoch+1}, Val Loss: {val_loss}')
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                print("New best validation score achieved, saving model...")
                self.save_params()
        return 
    
    @staticmethod
    def evaluation_step(state: Any, 
                        inputs: jnp.ndarray,
                        targets: jnp.ndarray) -> Tuple[Any, jnp.ndarray]:
        """
        Performs a single training step.

        Args:
            state: The current state of the model, including parameters and optimizer state.
            batch: A dictionary containing 'inputs' and 'targets' as keys, representing the input data.

        Returns:
            A tuple of the updated state and the loss value for this step.
        """
        logits = state.apply_fn({'params': state.params}, inputs,  rngs={'dropout': jax.random.PRNGKey(2)})
        return optax.softmax_cross_entropy_with_integer_labels(logits, targets).mean()

    def evaluate(self, 
                 test_loader: Iterable[Tuple[jnp.ndarray, jnp.ndarray]]) -> None:
        """
        evaluates the model using the provided validation loader.

        Args:
            val_loader: An iterable of validation data batches.
            epoch: The current epoch number.
            num_epochs: The total number of epochs.
        """
        total_loss = 0.0
        count = 0
        for inputs, targets in test_loader:
            batch_size = inputs.shape[0]
            batch_size_per_device = batch_size // self.num_devices
            inputs = inputs.reshape((self.num_devices, batch_size_per_device, -1))
            targets = targets.reshape((self.num_devices, batch_size_per_device, -1))
            loss = self.evaluation_step(self.state, inputs, targets)
            total_loss += jnp.mean(loss)
            count += 1
        
        mean_loss = total_loss / count
        return mean_loss

    def save_params(self) -> None:
        """
        Saves the model parameters to a file.
        """
        with open(self.weights_filename, 'wb') as f:
            pickle.dump(self.state.params, f)

    def load_params(self, filename: str) -> Any:
        """
        Loads the model parameters from a file.

        Args:
            filename: The filename of the file containing the parameters.

        Returns:
            The loaded parameters.
        """
        with open(filename, 'rb') as f:
            params = pickle.load(f)
        return params