#version 430 core

in vec2 v_texcoord;

uniform sampler2D uTexture;

out vec4 FragColor;

void main()
{
    vec4 tex = texture(uTexture, v_texcoord);

    FragColor = tex;
}