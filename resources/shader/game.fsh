#version 430 core

in vec2 v_texcoord;
uniform sampler2D uTexture;
out vec4 FragColor;
float alphaThreshold = 0;

void main()
{
    vec4 tex = texture(uTexture, v_texcoord);
    FragColor = tex;
    FragColor += vec4(.5, .5, .5, tex.a);
    if(tex.a <= alphaThreshold) {
        discard;
    }
}